"""Servicios de empresa: registro HU-11, edición del perfil HU-14, política de cancelación HU-19 y consulta/reglas RN-07.

Los demás módulos (sedes y productos) consultan las empresas a través de esta clase,
no acceden directamente al repositorio.
"""

import logging
from datetime import date
from typing import Protocol

from app.domain.empresa import (
    HORAS_MINIMAS_ANTELACION_DEFECTO,
    EmpresaCreate,
    EmpresaPerfilResponse,
    EmpresaResponse,
    EmpresaUpdate,
    EstadoEmpresa,
    PoliticaCancelacionResponse,
    PoliticaCancelacionUpdate,
    puede_publicar,
)
from app.domain.errores import (
    DatosInvalidos,
    ErrorDominio,
    OperacionNoPermitida,
    RecursoDuplicado,
    RecursoNoEncontrado,
    ServicioExternoNoDisponible,
)
from app.domain.imagen import ArchivoImagen, validar_imagenes
from app.repository.empresa_repository import EmpresaRepository
from app.service.almacenamiento_service import AlmacenamientoCloudinary, AlmacenamientoLocal
from app.service.correo_service import Correo, CorreoConsola
from app.service.plantillas_correo import correo_solicitud_empresa_recibida


logger = logging.getLogger(__name__)

SUBCARPETA_EMPRESAS = "empresas"


class ServicioCorreo(Protocol):
    def enviar(self, correo: Correo) -> None: ...


class EmpresaService:
    def __init__(
        self,
        repositorio: EmpresaRepository,
        correo: ServicioCorreo | None = None,
        almacenamiento: AlmacenamientoCloudinary | AlmacenamientoLocal | None = None,
    ) -> None:
        self._repositorio = repositorio
        self._almacenamiento = almacenamiento
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

    def actualizar_perfil(
        self, empresa_id: int, datos: EmpresaUpdate, logo: ArchivoImagen | None
    ) -> EmpresaPerfilResponse:
        """HU-14: edita descripción, contacto y logo. El NIT y la razón social no cambian (RN-06)."""
        empresa = self.obtener(empresa_id)

        if datos.nit is not None and datos.nit.strip() != empresa["nit"]:
            raise DatosInvalidos(
                "El NIT de la empresa no se puede modificar", {"empresa_id": empresa_id}
            )
        if datos.razon_social is not None and " ".join(datos.razon_social.split()) != empresa["razon_social"]:
            raise DatosInvalidos(
                "La razón social de la empresa no se puede modificar", {"empresa_id": empresa_id}
            )

        cambios = datos.model_dump(exclude_none=True, exclude={"nit", "razon_social"})
        if not cambios and logo is None:
            raise DatosInvalidos(
                "Debe enviar al menos un campo o un logo para actualizar", {"empresa_id": empresa_id}
            )

        logo_anterior = None
        if logo is not None:
            validar_imagenes([logo], obligatorio=True, recurso="logo")
            if self._almacenamiento is None:
                raise ServicioExternoNoDisponible(
                    "El almacenamiento de imágenes no está disponible", {"empresa_id": empresa_id}
                )
            guardado = self._almacenamiento.guardar(logo, f"{SUBCARPETA_EMPRESAS}/{empresa_id}")
            cambios["logo"] = vars(guardado)
            logo_anterior = empresa.get("logo")

        actualizada = self._repositorio.actualizar(empresa_id, cambios)
        if logo_anterior:
            self._borrar_logo_sin_fallar(logo_anterior)
        return self._a_perfil(actualizada)

    def _borrar_logo_sin_fallar(self, logo: dict) -> None:
        """Borra el logo reemplazado. Si falla, solo se registra: la edición ya quedó guardada."""
        try:
            self._almacenamiento.eliminar(logo["identificador"])
        except ErrorDominio:
            logger.warning("No se pudo borrar el logo anterior %s", logo["identificador"])

    @staticmethod
    def _a_perfil(empresa: dict) -> EmpresaPerfilResponse:
        logo = empresa.get("logo")
        return EmpresaPerfilResponse(
            empresa_id=empresa["empresa_id"],
            razon_social=empresa["razon_social"],
            descripcion=empresa.get("descripcion"),
            telefono=empresa.get("telefono"),
            correo_contacto=empresa.get("correo_contacto"),
            logo_url=logo["url"] if logo else None,
        )

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