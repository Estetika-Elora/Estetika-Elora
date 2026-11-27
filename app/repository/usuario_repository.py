"""Repositorio de usuarios en memoria (lista de diccionarios).

Los datos se pierden al reiniciar el servidor. Cuando se defina la base de datos, solo
cambia esta clase; el servicio sigue usando los mismos métodos.
"""

import copy
import threading


class UsuarioRepository:
    def __init__(self, id_inicial: int = 125) -> None:
        self._usuarios: list[dict] = []
        self._siguiente_id = id_inicial
        self._candado = threading.Lock()

    def crear(self, datos: dict) -> dict | None:
        """Guarda el usuario. Devuelve None si el correo ya existe (como un índice único)."""
        with self._candado:
            if any(u["correo"] == datos["correo"] for u in self._usuarios):
                return None
            usuario = {"usuario_id": self._siguiente_id, **datos}
            self._usuarios.append(usuario)
            self._siguiente_id += 1
            return copy.deepcopy(usuario)

    def obtener_por_id(self, usuario_id: int) -> dict | None:
        for usuario in self._usuarios:
            if usuario["usuario_id"] == usuario_id:
                return copy.deepcopy(usuario)
        return None

    def obtener_por_correo(self, correo: str) -> dict | None:
        for usuario in self._usuarios:
            if usuario["correo"] == correo:
                return copy.deepcopy(usuario)
        return None

    def actualizar(self, usuario_id: int, cambios: dict) -> dict | None:
        with self._candado:
            for usuario in self._usuarios:
                if usuario["usuario_id"] == usuario_id:
                    usuario.update(cambios)
                    return copy.deepcopy(usuario)
        return None

    def eliminar(self, usuario_id: int) -> dict | None:
        with self._candado:
            for indice, usuario in enumerate(self._usuarios):
                if usuario["usuario_id"] == usuario_id:
                    return self._usuarios.pop(indice)
        return None


usuario_repository = UsuarioRepository()
