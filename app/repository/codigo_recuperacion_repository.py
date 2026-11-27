"""Repositorio en memoria de los códigos de recuperación de contraseña (HU-03).

Cada registro liga un código con su usuario:
{"codigo_id", "usuario_id", "codigo_hash", "creado_en", "expira_en", "usado", "intentos"}

Se guarda el hash SHA-256 del código, no el código. `intentos` cuenta los códigos erróneos
digitados contra este registro. Equivale a una tabla `codigos_recuperacion` con llave foránea
a `usuarios`.
"""

import copy
import threading


class CodigoRecuperacionRepository:
    def __init__(self) -> None:
        self._codigos: list[dict] = []
        self._siguiente_id = 1
        self._candado = threading.Lock()

    def crear(self, datos: dict) -> dict:
        with self._candado:
            registro = {"codigo_id": self._siguiente_id, **datos, "usado": False, "intentos": 0}
            self._codigos.append(registro)
            self._siguiente_id += 1
            return copy.deepcopy(registro)

    def ultimo_de_usuario(self, usuario_id: int) -> dict | None:
        """El código más reciente del usuario, usado o no."""
        del_usuario = [c for c in self._codigos if c["usuario_id"] == usuario_id]
        return copy.deepcopy(max(del_usuario, key=lambda c: c["codigo_id"])) if del_usuario else None

    def sumar_intento(self, codigo_id: int, maximo: int) -> int:
        """Suma un intento fallido y devuelve el total. Al llegar al máximo el código se invalida."""
        with self._candado:
            for registro in self._codigos:
                if registro["codigo_id"] == codigo_id:
                    registro["intentos"] += 1
                    if registro["intentos"] >= maximo:
                        registro["usado"] = True
                    return registro["intentos"]
        return 0

    def marcar_usado(self, codigo_id: int) -> bool:
        """Marca el código como usado. Devuelve False si ya lo estaba (evita doble uso)."""
        with self._candado:
            for registro in self._codigos:
                if registro["codigo_id"] == codigo_id:
                    if registro["usado"]:
                        return False
                    registro["usado"] = True
                    return True
        return False

    def invalidar_de_usuario(self, usuario_id: int) -> None:
        """Deja sin efecto los códigos del usuario: solo sirve el último enviado."""
        with self._candado:
            for registro in self._codigos:
                if registro["usuario_id"] == usuario_id:
                    registro["usado"] = True


codigo_recuperacion_repository = CodigoRecuperacionRepository()
