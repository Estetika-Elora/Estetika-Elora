"""Servicio de sedes (HU-16 · PRO-16): CRUD de sedes con dirección validada en el mapa."""

from app.domain.errores import DatosInvalidos, RecursoNoEncontrado
from app.domain.estados import EstadoRegistro
from app.domain.sede import SedeCreate, SedeResponse, SedeUpdate
from app.repository.sede_repository import SedeRepository
from app.service.empresa_service import EmpresaService
from app.service.mapas_service import Coordenadas, MapasService


class SedeService:
    def __init__(
        self,
        repositorio: SedeRepository,
        empresa_service: EmpresaService,
        mapas_service: MapasService,
    ) -> None:
        self._repositorio = repositorio
        self._empresas = empresa_service
        self._mapas = mapas_service

    def crear(self, empresa_id: int, datos: SedeCreate) -> SedeResponse:
        self._empresas.verificar_aprobada(empresa_id)  # RN-07
        coordenadas = self._validar_direccion(datos.direccion, datos.ciudad)
        sede = self._repositorio.crear(
            {
                "empresa_id": empresa_id,
                **datos.model_dump(),
                "latitud": coordenadas.latitud,
                "longitud": coordenadas.longitud,
                "estado": EstadoRegistro.ACTIVE,
            }
        )
        return SedeResponse.model_validate(sede)

    def listar(self, empresa_id: int) -> list[SedeResponse]:
        self._empresas.obtener(empresa_id)
        return [SedeResponse.model_validate(s) for s in self._repositorio.listar_por_empresa(empresa_id)]

    def obtener(self, empresa_id: int, sede_id: int) -> SedeResponse:
        self._empresas.obtener(empresa_id)
        return SedeResponse.model_validate(self._buscar_de_empresa(empresa_id, sede_id))

    def actualizar(self, empresa_id: int, sede_id: int, datos: SedeUpdate) -> SedeResponse:
        self._empresas.verificar_aprobada(empresa_id)  # RN-07
        sede = self._buscar_de_empresa(empresa_id, sede_id)
        cambios = datos.model_dump(exclude_none=True)

        direccion = cambios.get("direccion", sede["direccion"])
        ciudad = cambios.get("ciudad", sede["ciudad"])
        if direccion != sede["direccion"] or ciudad != sede["ciudad"]:
            coordenadas = self._validar_direccion(direccion, ciudad)
            cambios["latitud"] = coordenadas.latitud
            cambios["longitud"] = coordenadas.longitud

        return SedeResponse.model_validate(self._repositorio.actualizar(sede_id, cambios))

    def eliminar(self, empresa_id: int, sede_id: int) -> SedeResponse:
        # Pendiente RN-10: no borrar una sede con reservas futuras (cuando exista MOD-05).
        self._empresas.verificar_aprobada(empresa_id)  # RN-07
        self._buscar_de_empresa(empresa_id, sede_id)
        return SedeResponse.model_validate(self._repositorio.eliminar(sede_id))

    def _buscar_de_empresa(self, empresa_id: int, sede_id: int) -> dict:
        """Una sede de otra empresa se trata como inexistente."""
        sede = self._repositorio.obtener_por_id(sede_id)
        if sede is None or sede["empresa_id"] != empresa_id:
            raise RecursoNoEncontrado("La sede no existe", {"sede_id": sede_id})
        return sede

    def _validar_direccion(self, direccion: str, ciudad: str) -> Coordenadas:
        coordenadas = self._mapas.geocodificar(direccion, ciudad)
        if coordenadas is None:
            raise DatosInvalidos(
                "La dirección no pudo ser validada en el mapa",
                {"direccion": direccion, "ciudad": ciudad},
            )
        return coordenadas
