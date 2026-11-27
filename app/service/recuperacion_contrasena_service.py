"""Servicio de recuperación de contraseña (HU-03 · PRO-03).

Flujo:
1. `solicitar_codigo`: si el correo es de una cuenta ACTIVE, genera un código de 6 dígitos,
   lo envía al correo (API-E03) y guarda su hash con vigencia de 15 minutos. Los códigos
   anteriores dejan de servir. La respuesta es la misma exista o no la cuenta, para no revelar
   qué correos están registrados; por eso, si se pide otro código antes de 60 segundos, no se
   envía nada y tampoco se responde 429. Si el correo no se puede enviar, no se guarda el
   código y se responde 503.
2. `cambiar_contrasena`: el código debe ser el último enviado, estar vigente y sin usar. Cada
   código erróneo suma un intento; al quinto el código se invalida. Con un código válido se
   marca como usado, se guarda la contraseña nueva con bcrypt y se quita el bloqueo de RN-03.
   Cualquier fallo responde 400 con el mismo mensaje.
"""

from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

from app.domain.errores import DatosInvalidos
from app.domain.usuario import (
    DIGITOS_CODIGO_RECUPERACION,
    MAXIMO_INTENTOS_CODIGO_RECUPERACION,
    MINUTOS_VIGENCIA_CODIGO_RECUPERACION,
    CambioContrasena,
    ContrasenaActualizadaResponse,
    EstadoCuenta,
    RecuperacionResponse,
)
from app.repository.codigo_recuperacion_repository import CodigoRecuperacionRepository
from app.repository.usuario_repository import UsuarioRepository
from app.service import seguridad_service
from app.service.correo_service import Correo
from app.service.plantillas_correo import correo_recuperacion_contrasena

MENSAJE_CODIGO_INVALIDO = "El código no es válido o ya venció"


class ServicioCorreo(Protocol):
    def enviar(self, correo: Correo) -> None: ...


def _ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


class RecuperacionContrasenaService:
    def __init__(
        self,
        usuarios: UsuarioRepository,
        codigos: CodigoRecuperacionRepository,
        correo: ServicioCorreo,
        espera_reenvio_segundos: int = 60,
        reloj: Callable[[], datetime] = _ahora_utc,
    ) -> None:
        self._usuarios = usuarios
        self._codigos = codigos
        self._correo = correo
        self._vigencia = timedelta(minutes=MINUTOS_VIGENCIA_CODIGO_RECUPERACION)
        self._espera_reenvio = timedelta(seconds=espera_reenvio_segundos)
        self._reloj = reloj

    def solicitar_codigo(self, correo: str) -> RecuperacionResponse:
        respuesta = RecuperacionResponse(
            correo=correo, vigencia_minutos=MINUTOS_VIGENCIA_CODIGO_RECUPERACION
        )
        usuario = self._usuarios.obtener_por_correo(correo)
        if usuario is None or usuario["estado"] != EstadoCuenta.ACTIVE:
            return respuesta

        ultimo = self._codigos.ultimo_de_usuario(usuario["usuario_id"])
        if ultimo is not None and self._reloj() < ultimo["creado_en"] + self._espera_reenvio:
            return respuesta

        codigo = seguridad_service.generar_codigo_numerico(DIGITOS_CODIGO_RECUPERACION)
        self._correo.enviar(
            correo_recuperacion_contrasena(
                usuario["correo"], usuario["nombre"], codigo, MINUTOS_VIGENCIA_CODIGO_RECUPERACION
            )
        )

        ahora = self._reloj()
        self._codigos.invalidar_de_usuario(usuario["usuario_id"])
        self._codigos.crear(
            {
                "usuario_id": usuario["usuario_id"],
                "codigo_hash": seguridad_service.hash_token(codigo),
                "creado_en": ahora,
                "expira_en": ahora + self._vigencia,
            }
        )
        return respuesta

    def cambiar_contrasena(self, datos: CambioContrasena) -> ContrasenaActualizadaResponse:
        rechazo = DatosInvalidos(MENSAJE_CODIGO_INVALIDO, {"correo": datos.correo})

        usuario = self._usuarios.obtener_por_correo(datos.correo)
        if usuario is None or usuario["estado"] != EstadoCuenta.ACTIVE:
            raise rechazo

        registro = self._codigos.ultimo_de_usuario(usuario["usuario_id"])
        ahora = self._reloj()
        if registro is None or registro["usado"] or ahora >= registro["expira_en"]:
            raise rechazo

        recibido = seguridad_service.hash_token(datos.codigo)
        if not seguridad_service.coinciden_hashes(recibido, registro["codigo_hash"]):
            self._codigos.sumar_intento(registro["codigo_id"], MAXIMO_INTENTOS_CODIGO_RECUPERACION)
            raise rechazo
        if not self._codigos.marcar_usado(registro["codigo_id"]):
            raise rechazo

        self._usuarios.actualizar(
            usuario["usuario_id"],
            {
                "contrasena_hash": seguridad_service.hashear_contrasena(datos.nueva_contrasena),
                "intentos_fallidos": 0,
                "bloqueado_hasta": None,
            },
        )
        return ContrasenaActualizadaResponse(correo=usuario["correo"], fecha_cambio=ahora)
