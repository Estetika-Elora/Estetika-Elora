"""Repositorio de sedes en memoria (lista de diccionarios).

Los datos se pierden al reiniciar el servidor. Cuando se defina la base de datos, solo
cambia esta clase; el servicio sigue usando los mismos métodos.
"""

import copy


class SedeRepository:
    def __init__(self, id_inicial: int = 41) -> None:
        # Empieza en 41 para que coincida con los casos de prueba de HU-16.
        self._sedes: list[dict] = []
        self._siguiente_id = id_inicial

    def crear(self, datos: dict) -> dict:
        sede = {"sede_id": self._siguiente_id, **datos}
        self._sedes.append(sede)
        self._siguiente_id += 1
        return copy.deepcopy(sede)

    def obtener_por_id(self, sede_id: int) -> dict | None:
        for sede in self._sedes:
            if sede["sede_id"] == sede_id:
                return copy.deepcopy(sede)
        return None

    def listar_por_empresa(self, empresa_id: int) -> list[dict]:
        return [copy.deepcopy(s) for s in self._sedes if s["empresa_id"] == empresa_id]

    def actualizar(self, sede_id: int, cambios: dict) -> dict | None:
        for sede in self._sedes:
            if sede["sede_id"] == sede_id:
                sede.update(cambios)
                return copy.deepcopy(sede)
        return None

    def eliminar(self, sede_id: int) -> dict | None:
        for indice, sede in enumerate(self._sedes):
            if sede["sede_id"] == sede_id:
                return self._sedes.pop(indice)
        return None


# Instancia única compartida por toda la aplicación.
sede_repository = SedeRepository()
