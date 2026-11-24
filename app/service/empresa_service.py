"""Servicios de empresa: registro HU-11, política de cancelación HU-19 y consulta/reglas RN-07.

Los demás módulos (sedes y productos) consultan las empresas a través de esta clase,
no acceden directamente al repositorio.
"""

from datetime import date
from typing import Protocol

from app.domain.empresa import (
    HORAS_MINIMAS_ANTELACION_DEFECTO,
    EmpresaCreate,
    EmpresaResponse,
    EstadoEmpresa,
    PoliticaCancelacionResponse,
    PoliticaCancelacionUpdate,
    puede_publicar,
)
from app.domain.errores import (
    OperacionNoPermitida,
    RecursoDuplicado,
    RecursoNoEncontrado,
    ServicioExternoNoDisponible,
)
from app.repository.empresa_repository import EmpresaRepository
from app.service.correo_service import Correo, CorreoConsola
from app.service.plantillas_correo import correo_solicitud_empresa_recibida


class ServicioCorreo(Protocol):
    def enviar(self, correo: Correo) -> None: ...


class EmpresaService:
    def __init__(
        self,
        repositorio: EmpresaRepository,
        correo: ServicioCorreo | None = None,
    ) -> None:
        self._repositorio = repositorio
        # El correo es opcional para no alterar los consumidores internos (sedes/productos).
        self._correo = correo or CorreoConsola()

    def registrar(self, datos: EmpresaCreate) -> EmpresaResponse:
        """RN-06: registra NIT único, asigna PENDING_APPROVAL y confirma por correo."""
        existente = self._repositorio.obtener_por_nit(datos.nit)
        if existente is not None:
            raise RecursoDuplicado(
                "El NIT ya se encuentra registrado",
                {"nit": datos.nit},
            )

        empresa = self._repositorio.crear(
            {
                **datos.model_dump(),
                "estado": EstadoEmpresa.PENDING_APPROVAL,
            }
        )
        # La verificación también se hace dentro del repositorio para evitar duplicados
        # si dos solicitudes concurrentes intentan registrar el mismo NIT.
        if empresa is None:
            raise RecursoDuplicado(
                "El NIT ya se encuentra registrado",
                {"nit": datos.nit},
            )

        correo = correo_solicitud_empresa_recibida(
            destinatario=empresa["correo_representante"],
            nombre=empresa["representante"],
            razon_social=empresa["razon_social"],
            nit=empresa["nit"],
        )
        try:
            self._correo.enviar(correo)
        except ServicioExternoNoDisponible:
            # Evita dejar una solicitud registrada cuando no se pudo confirmar recepción.
            self._repositorio.eliminar(empresa["empresa_id"])
            raise

        return EmpresaResponse.model_validate(empresa)

    def obtener(self, empresa_id: int) -> dict:
        empresa = self._repositorio.obtener_por_id(empresa_id)
        if empresa is None:
            raise RecursoNoEncontrado(
                "La empresa no existe",
                {"empresa_id": empresa_id},
            )
        return empresa

    def verificar_aprobada(self, empresa_id: int) -> dict:
        """RN-07: lanza 403 si la empresa no está aprobada para publicar."""
        empresa = self.obtener(empresa_id)
        estado = empresa["estado"]
        if not isinstance(estado, EstadoEmpresa):
            estado = EstadoEmpresa(estado)

        if not puede_publicar(estado):
            raise OperacionNoPermitida(
                "La empresa no está aprobada para publicar en la plataforma",
                {"empresa_id": empresa_id, "estado": estado.value},
            )
        return empresa
    
    def configurar_politica_cancelacion(
        self, empresa_id: int, datos: PoliticaCancelacionUpdate
    ) -> PoliticaCancelacionResponse:
        """RN-24: guarda la política para toda la empresa. Solo empresas aprobadas (RN-07)."""
        self.verificar_aprobada(empresa_id)
        politica = {
            "horas_minimas_antelacion": datos.horas_minimas_antelacion,
            "vigente_desde": date.today(),
        }
        self._repositorio.actualizar(empresa_id, {"politica_cancelacion": politica})
        return PoliticaCancelacionResponse(empresa_id=empresa_id, **politica)

    def obtener_politica_cancelacion(self, empresa_id: int) -> PoliticaCancelacionResponse:
        """API-I02: política vigente; si la empresa no ha configurado una, aplica 24 horas."""
        empresa = self.obtener(empresa_id)
        politica = empresa.get("politica_cancelacion") or {
            "horas_minimas_antelacion": HORAS_MINIMAS_ANTELACION_DEFECTO,
            "vigente_desde": None,
        }
        return PoliticaCancelacionResponse(empresa_id=empresa_id, **politica)

    def listar(self) -> list[EmpresaResponse]:
        """Devuelve todas las empresas registradas."""
        empresas = self._repositorio.listar()

        return [
            EmpresaResponse.model_validate(empresa)
            for empresa in empresas
        ]