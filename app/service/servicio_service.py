"""Servicio de servicios del catálogo: lo que otros módulos necesitan consultar de un servicio.

Los horarios (HU-23) y las reservas (HU-37) no leen el repositorio de servicios
directamente; pasan por aquí, que hace las veces de API interna del módulo MOD-03.
"""

from app.domain.errores import PrecondicionNoCumplida, RecursoNoEncontrado
from app.domain.servicio import esta_activo, se_ofrece_en
from app.repository.servicio_repository import ServicioRepository


class ServicioService:
    def __init__(self, repositorio: ServicioRepository) -> None:
        self._repositorio = repositorio

    def obtener(self, servicio_id: int) -> dict:
        servicio = self._repositorio.obtener_por_id(servicio_id)
        if servicio is None:
            raise RecursoNoEncontrado("El servicio no existe", {"servicio_id": servicio_id})
        return servicio

    def obtener_ofrecido_en_sede(self, servicio_id: int, sede_id: int) -> dict:
        """El servicio debe existir, ofrecerse en la sede y estar activo."""
        servicio = self.obtener(servicio_id)
        if not se_ofrece_en(servicio, sede_id):
            raise RecursoNoEncontrado(
                "El servicio no se ofrece en la sede indicada",
                {"servicio_id": servicio_id, "sede_id": sede_id},
            )
        if not esta_activo(servicio["estado"]):
            raise PrecondicionNoCumplida(
                "El servicio no está activo",
                {"servicio_id": servicio_id, "estado": servicio["estado"].value},
            )
        return servicio

    def listar_activos_de_sede(self, sede_id: int) -> list[dict]:
        return [s for s in self._repositorio.listar_por_sede(sede_id) if esta_activo(s["estado"])]
