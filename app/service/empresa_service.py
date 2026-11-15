"""Servicio de empresas: lo que otros módulos necesitan consultar de una empresa.

Otros servicios (sedes, productos) no leen el repositorio de empresas directamente;
pasan por este servicio, que hace las veces de API interna del módulo MOD-02.
"""

from app.domain.empresa import puede_publicar
from app.domain.errores import OperacionNoPermitida, RecursoNoEncontrado
from app.repository.empresa_repository import EmpresaRepository


class EmpresaService:
    def __init__(self, repositorio: EmpresaRepository) -> None:
        self._repositorio = repositorio

    def obtener(self, empresa_id: int) -> dict:
        empresa = self._repositorio.obtener_por_id(empresa_id)
        if empresa is None:
            raise RecursoNoEncontrado("La empresa no existe", {"empresa_id": empresa_id})
        return empresa

    def verificar_aprobada(self, empresa_id: int) -> dict:
        """RN-07: lanza 403 si la empresa no está aprobada para publicar."""
        empresa = self.obtener(empresa_id)
        if not puede_publicar(empresa["estado"]):
            raise OperacionNoPermitida(
                "La empresa no está aprobada para publicar en la plataforma",
                {"empresa_id": empresa_id, "estado": empresa["estado"].value},
            )
        return empresa
