"""Servicio de autenticación (HU-02 · PRO-02): inicio de sesión seguro con JWT.

Orden de las validaciones en `iniciar_sesion`:
1. El correo debe existir; si no, 401 con el mismo mensaje que una contraseña incorrecta.
   Igual se compara contra un hash de relleno para que la respuesta tarde lo mismo.
2. Si la cuenta está bloqueada (RN-03), 423 aunque la contraseña sea correcta.
3. Contraseña incorrecta: suma un intento. Al quinto seguido la cuenta se bloquea 15 minutos.
4. La contraseña se revisa antes que el estado: así no se revela si una cuenta está pendiente
   o suspendida a quien no conoce la contraseña. Solo una cuenta ACTIVE recibe token (403).
5. Con login exitoso los intentos vuelven a 0 y se entrega el JWT con el rol del usuario.
"""

import threading
from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Callable

from app.domain.auth import MAXIMO_INTENTOS_FALLIDOS, MINUTOS_BLOQUEO, LoginRequest, LoginResponse
from app.domain.errores import CredencialesInvalidas, CuentaBloqueada, OperacionNoPermitida
from app.domain.usuario import EstadoCuenta
from app.repository.usuario_repository import UsuarioRepository
from app.service import seguridad_service

_MENSAJE_CREDENCIALES = "Correo o contraseña incorrectos"
_HASH_RELLENO = seguridad_service.hashear_contrasena("Relleno-para-igualar-tiempos-1")


def _ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


class AuthService:
    def __init__(
        self,
        repositorio: UsuarioRepository,
        secreto: str,
        minutos_token: int = 60,
        reloj: Callable[[], datetime] = _ahora_utc,
    ) -> None:
        self._repositorio = repositorio
        self._secreto = secreto
        self._minutos_token = minutos_token
        self._reloj = reloj
        self._candado = threading.Lock()

    def iniciar_sesion(self, datos: LoginRequest) -> LoginResponse:
        usuario = self._repositorio.obtener_por_correo(datos.correo)
        if usuario is None:
            seguridad_service.verificar_contrasena(datos.contrasena, _HASH_RELLENO)
            raise CredencialesInvalidas(_MENSAJE_CREDENCIALES, {})

        contrasena_correcta = seguridad_service.verificar_contrasena(
            datos.contrasena, usuario["contrasena_hash"]
        )

        with self._candado:
            usuario = self._repositorio.obtener_por_id(usuario["usuario_id"])
            ahora = self._reloj()
            self._verificar_no_bloqueada(usuario, ahora)
            if not contrasena_correcta:
                self._registrar_intento_fallido(usuario, ahora)
            self._verificar_estado(usuario)
            self._repositorio.actualizar(
                usuario["usuario_id"], {"intentos_fallidos": 0, "bloqueado_hasta": None}
            )

        token = seguridad_service.crear_token_acceso(
            usuario["usuario_id"], usuario["rol"].value, self._secreto, ahora, self._minutos_token
        )
        return LoginResponse(
            usuario_id=usuario["usuario_id"],
            nombre=usuario["nombre"],
            rol=usuario["rol"],
            token=token,
            expira_en=self._minutos_token * 60,
        )

    def _verificar_no_bloqueada(self, usuario: dict, ahora: datetime) -> None:
        bloqueado_hasta = usuario.get("bloqueado_hasta")
        if bloqueado_hasta is not None and ahora < bloqueado_hasta:
            minutos = ceil((bloqueado_hasta - ahora).total_seconds() / 60)
            raise CuentaBloqueada(
                f"La cuenta está bloqueada por intentos fallidos. Intente de nuevo en {minutos} minutos",
                {"minutos_restantes": minutos},
            )

    def _registrar_intento_fallido(self, usuario: dict, ahora: datetime) -> None:
        intentos = usuario.get("intentos_fallidos", 0) + 1
        if intentos >= MAXIMO_INTENTOS_FALLIDOS:
            self._repositorio.actualizar(
                usuario["usuario_id"],
                {"intentos_fallidos": 0, "bloqueado_hasta": ahora + timedelta(minutes=MINUTOS_BLOQUEO)},
            )
            raise CuentaBloqueada(
                f"Se superaron los {MAXIMO_INTENTOS_FALLIDOS} intentos fallidos. "
                f"La cuenta queda bloqueada {MINUTOS_BLOQUEO} minutos",
                {"minutos_restantes": MINUTOS_BLOQUEO},
            )
        self._repositorio.actualizar(
            usuario["usuario_id"], {"intentos_fallidos": intentos, "bloqueado_hasta": None}
        )
        raise CredencialesInvalidas(
            _MENSAJE_CREDENCIALES, {"intentos_restantes": MAXIMO_INTENTOS_FALLIDOS - intentos}
        )

    def _verificar_estado(self, usuario: dict) -> None:
        if usuario["estado"] == EstadoCuenta.PENDING_VERIFICATION:
            raise OperacionNoPermitida("Debe activar su cuenta antes de iniciar sesión", {})
        if usuario["estado"] != EstadoCuenta.ACTIVE:
            raise OperacionNoPermitida("La cuenta está suspendida. Comuníquese con el administrador", {})
