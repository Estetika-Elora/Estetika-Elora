"""Repositorio en memoria de los tokens de verificación de correo (HU-01).

Cada registro liga un token con su usuario:
{"token_hash", "usuario_id", "creado_en", "expira_en", "usado"}

Se guarda el hash SHA-256 del token, no el token: si alguien leyera estos datos no podría
armar un enlace de activación válido. Equivale a una tabla `tokens_verificacion` con llave
foránea a `usuarios`.
"""

import copy
import threading


class TokenVerificacionRepository:
    def __init__(self) -> None:
        self._tokens: list[dict] = []
        self._candado = threading.Lock()

    def crear(self, datos: dict) -> dict:
        with self._candado:
            registro = {**datos, "usado": False}
            self._tokens.append(registro)
            return copy.deepcopy(registro)

    def obtener_por_hash(self, token_hash: str) -> dict | None:
        for registro in self._tokens:
            if registro["token_hash"] == token_hash:
                return copy.deepcopy(registro)
        return None

    def ultimo_de_usuario(self, usuario_id: int) -> dict | None:
        """El token más reciente del usuario (para la espera entre reenvíos)."""
        del_usuario = [t for t in self._tokens if t["usuario_id"] == usuario_id]
        return copy.deepcopy(max(del_usuario, key=lambda t: t["creado_en"])) if del_usuario else None

    def marcar_usado(self, token_hash: str) -> bool:
        """Marca el token como usado. Devuelve False si ya lo estaba (evita doble uso)."""
        with self._candado:
            for registro in self._tokens:
                if registro["token_hash"] == token_hash:
                    if registro["usado"]:
                        return False
                    registro["usado"] = True
                    return True
        return False

    def invalidar_de_usuario(self, usuario_id: int) -> None:
        """Deja sin efecto todos los tokens del usuario: solo sirve el último enlace enviado."""
        with self._candado:
            for registro in self._tokens:
                if registro["usuario_id"] == usuario_id:
                    registro["usado"] = True

    def eliminar_de_usuario(self, usuario_id: int) -> None:
        with self._candado:
            self._tokens = [t for t in self._tokens if t["usuario_id"] != usuario_id]


token_verificacion_repository = TokenVerificacionRepository()
