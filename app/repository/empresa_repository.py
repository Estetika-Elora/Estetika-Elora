"""Repositorio de empresas en memoria.

Mantiene la misma interfaz utilizada por los módulos de sedes y productos. Los datos
se pierden al reiniciar el servidor; la persistencia en una base de datos se implementará
cuando se incorpore esa infraestructura al proyecto.
"""

import copy
import threading

from app.domain.empresa import EstadoEmpresa


class EmpresaRepository:
    def __init__(self) -> None:
        # Datos semilla necesarios para las HU de sedes y productos.
        self._empresas: list[dict] = [
            {
                "empresa_id": 18,
                "nit": "900456789-1",
                "razon_social": "Elora Spa S.A.S.",
                "categoria": "Spa y estética",
                "representante": "Administración Elora",
                "estado": EstadoEmpresa.APPROVED,
            },
            {
                "empresa_id": 19,
                "nit": "901234567-3",
                "razon_social": "Belleza Natural S.A.S.",
                "categoria": "Estética",
                "representante": "Representante Belleza Natural",
                "estado": EstadoEmpresa.PENDING_APPROVAL,
            },
        ]
        self._siguiente_id = max(e["empresa_id"] for e in self._empresas) + 1
        self._candado = threading.RLock()

    def obtener_por_id(self, empresa_id: int) -> dict | None:
        with self._candado:
            for empresa in self._empresas:
                if empresa["empresa_id"] == empresa_id:
                    return copy.deepcopy(empresa)
        return None

    def listar(self) -> list[dict]:
        with self._candado:
            return copy.deepcopy(self._empresas)

    def obtener_por_nit(self, nit: str) -> dict | None:
        with self._candado:
            for empresa in self._empresas:
                if empresa["nit"] == nit:
                    return copy.deepcopy(empresa)
        return None

    def crear(self, datos: dict) -> dict | None:
        """Crea la empresa; devuelve None si el NIT ya existe (restricción de unicidad)."""
        with self._candado:
            if any(empresa["nit"] == datos["nit"] for empresa in self._empresas):
                return None

            nueva_empresa = {
                **copy.deepcopy(datos),
                "empresa_id": self._siguiente_id,
            }
            self._empresas.append(nueva_empresa)
            self._siguiente_id += 1
            return copy.deepcopy(nueva_empresa)

    def eliminar(self, empresa_id: int) -> dict | None:
        """Elimina una empresa creada si debe revertirse una operación fallida."""
        with self._candado:
            for indice, empresa in enumerate(self._empresas):
                if empresa["empresa_id"] == empresa_id:
                    eliminada = self._empresas.pop(indice)
                    return copy.deepcopy(eliminada)
        return None


# Instancia única compartida por toda la aplicación.
empresa_repository = EmpresaRepository()
