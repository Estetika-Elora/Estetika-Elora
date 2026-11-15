"""Repositorio de empresas en memoria (lista de diccionarios).

Mínimo necesario para HU-16 y HU-31: solo consulta. El CRUD de empresas llega con HU-11.
Datos semilla coherentes con los casos de prueba de las HU:
- Empresa 18: aprobada (puede publicar sedes y productos).
- Empresa 19: pendiente de aprobación (debe recibir 403).
"""

import copy

from app.domain.empresa import EstadoEmpresa


class EmpresaRepository:
    def __init__(self) -> None:
        self._empresas: list[dict] = [
            {
                "empresa_id": 18,
                "nit": "900456789-1",
                "razon_social": "Elora Spa S.A.S.",
                "estado": EstadoEmpresa.APPROVED,
            },
            {
                "empresa_id": 19,
                "nit": "901234567-3",
                "razon_social": "Belleza Natural S.A.S.",
                "estado": EstadoEmpresa.PENDING_APPROVAL,
            },
        ]

    def obtener_por_id(self, empresa_id: int) -> dict | None:
        for empresa in self._empresas:
            if empresa["empresa_id"] == empresa_id:
                return copy.deepcopy(empresa)
        return None

    def listar(self) -> list[dict]:
        return copy.deepcopy(self._empresas)


# Instancia única compartida por toda la aplicación.
empresa_repository = EmpresaRepository()
