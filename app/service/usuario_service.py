"""Servicio de usuarios (HU-01 · PRO-01): registro con verificación por correo.

Flujo:
1. `registrar`: valida RN-01 (correo único), guarda la contraseña con hash, crea la cuenta en
   PENDING_VERIFICATION y envía el enlace de activación (API-E03). Si el correo no se puede
   enviar, la cuenta se borra y se responde 503, para que el usuario pueda reintentar.
2. `verificar`: el token del enlace identifica al usuario; si está vigente y sin usar, la
   cuenta pasa a ACTIVE.
3. `reenviar_verificacion`: nuevo enlace para una cuenta pendiente (extra a la HU-01, por si
   el correo nunca llegó). Invalida los enlaces anteriores y exige una espera entre envíos.
"""

from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

from app.domain.errores import (
    DatosInvalidos,
    DemasiadasSolicitudes,
    RecursoDuplicado,
    RecursoNoEncontrado,
    ServicioExternoNoDisponible,
)
from app.domain.usuario import (
    EstadoCuenta,
    ReenvioResponse,
    Rol,
    UsuarioCreate,
    UsuarioResponse,
)
from app.repository.token_verificacion_repository import TokenVerificacionRepository
from app.repository.usuario_repository import UsuarioRepository
from app.service import seguridad_service
from app.service.correo_service import Correo
from app.service.plantillas_correo import correo_activacion

RUTA_VERIFICACION = "/api/v1/usuarios/verificar"


class ServicioCorreo(Protocol):
    def enviar(self, correo: Correo) -> None: ...


def _ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


class UsuarioService:
    def __init__(
        self,
        repositorio: UsuarioRepository,
        tokens: TokenVerificacionRepository,
        correo: ServicioCorreo,
        url_base: str,
        vigencia_horas: int = 24,
        espera_reenvio_segundos: int = 60,
        reloj: Callable[[], datetime] = _ahora_utc,
    ) -> None:
        self._repositorio = repositorio
        self._tokens = tokens
        self._correo = correo
        self._url_base = url_base.rstrip("/")
        self._vigencia = timedelta(hours=vigencia_horas)
        self._vigencia_horas = vigencia_horas
        self._espera_reenvio = timedelta(seconds=espera_reenvio_segundos)
        self._reloj = reloj

    def registrar(self, datos: UsuarioCreate) -> UsuarioResponse:
        self._verificar_correo_disponible(datos.correo)
        usuario = self._repositorio.crear(
            {
                "nombre": datos.nombre,
                "correo": datos.correo,
                "telefono": datos.telefono,
                "contrasena_hash": seguridad_service.hashear_contrasena(datos.contrasena),
                "rol": Rol.USUARIO,
                "estado": EstadoCuenta.PENDING_VERIFICATION,
                "intentos_fallidos": 0,
                "bloqueado_hasta": None,
                "fecha_registro": self._reloj(),
            }
        )
        if usuario is None:
            self._verificar_correo_disponible(datos.correo)
            raise RecursoDuplicado("El correo ya se encuentra registrado", {"correo": datos.correo})

        try:
            self._enviar_enlace(usuario)
        except ServicioExternoNoDisponible:
            self._tokens.eliminar_de_usuario(usuario["usuario_id"])
            self._repositorio.eliminar(usuario["usuario_id"])
            raise
        return UsuarioResponse.model_validate(usuario)

    def verificar(self, token: str) -> UsuarioResponse:
        token_hash = seguridad_service.hash_token(token)
        registro = self._tokens.obtener_por_hash(token_hash)
        if registro is None:
            raise DatosInvalidos("El enlace de verificación no es válido", {})
        if registro["usado"]:
            raise DatosInvalidos("El enlace de verificación ya fue usado o fue reemplazado por uno nuevo", {})
        if self._reloj() >= registro["expira_en"]:
            raise DatosInvalidos("El enlace de verificación venció. Solicite uno nuevo", {})

        usuario = self._repositorio.obtener_por_id(registro["usuario_id"])
        if usuario is None or usuario["estado"] != EstadoCuenta.PENDING_VERIFICATION:
            raise DatosInvalidos("El enlace de verificación no es válido", {})
        if not self._tokens.marcar_usado(token_hash): 
            raise DatosInvalidos("El enlace de verificación ya fue usado o fue reemplazado por uno nuevo", {})

        activo = self._repositorio.actualizar(usuario["usuario_id"], {"estado": EstadoCuenta.ACTIVE})
        return UsuarioResponse.model_validate(activo)

    def reenviar_verificacion(self, correo: str) -> ReenvioResponse:
        usuario = self._repositorio.obtener_por_correo(correo)
        if usuario is None:
            raise RecursoNoEncontrado("No existe una cuenta registrada con ese correo", {"correo": correo})
        if usuario["estado"] == EstadoCuenta.ACTIVE:
            raise RecursoDuplicado("La cuenta ya está activada", {"correo": correo})
        if usuario["estado"] != EstadoCuenta.PENDING_VERIFICATION:
            raise RecursoDuplicado("La cuenta no está pendiente de verificación", {"correo": correo})

        ultimo = self._tokens.ultimo_de_usuario(usuario["usuario_id"])
        if ultimo is not None:
            disponible_en = ultimo["creado_en"] + self._espera_reenvio
            restante = (disponible_en - self._reloj()).total_seconds()
            if restante > 0:
                raise DemasiadasSolicitudes(
                    "Espere antes de solicitar otro correo de verificación",
                    {"segundos_restantes": int(restante) + 1},
                )

        self._enviar_enlace(usuario)
        return ReenvioResponse(correo=correo, vigencia_horas=self._vigencia_horas)

    def _verificar_correo_disponible(self, correo: str) -> None:
        existente = self._repositorio.obtener_por_correo(correo)
        if existente is None:
            return
        if existente["estado"] == EstadoCuenta.PENDING_VERIFICATION:
            raise RecursoDuplicado(
                "El correo ya se encuentra registrado y está pendiente de activación. "
                "Solicite un nuevo enlace de verificación",
                {"correo": correo},
            )
        raise RecursoDuplicado("El correo ya se encuentra registrado", {"correo": correo})

    def _enviar_enlace(self, usuario: dict) -> None:
        """Envía un enlace nuevo. Solo si el envío funciona se invalidan los anteriores."""
        token = seguridad_service.generar_token()
        enlace = f"{self._url_base}{RUTA_VERIFICACION}?token={token}"
        self._correo.enviar(
            correo_activacion(usuario["correo"], usuario["nombre"], enlace, self._vigencia_horas)
        )

        ahora = self._reloj()
        self._tokens.invalidar_de_usuario(usuario["usuario_id"])
        self._tokens.crear(
            {
                "token_hash": seguridad_service.hash_token(token),
                "usuario_id": usuario["usuario_id"],
                "creado_en": ahora,
                "expira_en": ahora + self._vigencia,
            }
        )
