"""Endpoints de usuarios (HU-01, HU-03). Solo llaman al servicio y convierten errores en HTTP."""

import os

from fastapi import APIRouter, Query, status

from app.api.respuestas import RespuestaApi, RespuestaError, a_http
from app.domain.errores import ErrorDominio
from app.domain.usuario import (
    CambioContrasena,
    ContrasenaActualizadaResponse,
    RecuperacionResponse,
    ReenvioResponse,
    SolicitudReenvio,
    SolicitudRecuperacion,
    UsuarioCreate,
    UsuarioResponse,
)
from app.repository.codigo_recuperacion_repository import codigo_recuperacion_repository
from app.repository.token_verificacion_repository import token_verificacion_repository
from app.repository.usuario_repository import usuario_repository
from app.service.correo_service import crear_servicio_correo
from app.service.recuperacion_contrasena_service import (
    MENSAJE_CODIGO_INVALIDO,
    RecuperacionContrasenaService,
)
from app.service.usuario_service import UsuarioService

router = APIRouter(prefix="/api/v1")


def _entero_env(nombre: str, por_defecto: int) -> int:
    try:
        return int(os.getenv(nombre, por_defecto))
    except ValueError:
        return por_defecto


correo = crear_servicio_correo()

servicio = UsuarioService(
    usuario_repository,
    token_verificacion_repository,
    correo,
    os.getenv("PUBLIC_BASE_URL", "http://localhost:8000"),
    vigencia_horas=_entero_env("TOKEN_VERIFICACION_HORAS", 24),
)

servicio_recuperacion = RecuperacionContrasenaService(
    usuario_repository,
    codigo_recuperacion_repository,
    correo,
)


def _error(descripcion: str, mensaje: str, data: dict) -> dict:
    return {
        "model": RespuestaError,
        "description": descripcion,
        "content": {"application/json": {"example": {"message": mensaje, "data": data, "success": False}}},
    }


_ERROR_503 = _error(
    "No hay conexión con el servicio de correo (API-E03)",
    "No fue posible enviar el correo en este momento. Intente más tarde",
    {},
)


@router.post(
    "/usuarios/registro",
    tags=["Usuarios (HU-01)"],
    status_code=status.HTTP_201_CREATED,
    response_model=RespuestaApi[UsuarioResponse],
    responses={
        400: _error(
            "Algún dato no tiene formato válido o la contraseña no cumple RN-02",
            "La contraseña debe tener mínimo 8 caracteres, una letra mayúscula y un número",
            {"contrasena": "clave"},
        ),
        409: _error(
            "El correo ya está registrado (RN-01)",
            "El correo ya se encuentra registrado",
            {"correo": "laura.gomez@gmail.com"},
        ),
        503: _ERROR_503,
    },
    summary="Registrarse en la plataforma con verificación por correo",
    description=(
        "Crea una cuenta con rol «usuario» en estado PENDING_VERIFICATION y envía al correo un "
        "enlace de activación que vence en 24 horas (API-E03). El correo debe ser único (RN-01) "
        "y la contraseña tener mínimo 8 caracteres, una mayúscula y un número (RN-02); se guarda "
        "con hash bcrypt. Si el correo no se puede enviar, la cuenta no se crea (503)."
    ),
)
def registrar_usuario(datos: UsuarioCreate):
    try:
        usuario = servicio.registrar(datos)
    except ErrorDominio as error:
        raise a_http(error) from error
    return RespuestaApi(message="Usuario registrado. Revise su correo para activar la cuenta", data=usuario)


@router.get(
    "/usuarios/verificar",
    tags=["Usuarios (HU-01)"],
    response_model=RespuestaApi[UsuarioResponse],
    responses={
        400: _error(
            "El token no existe, ya se usó o venció",
            "El enlace de verificación venció. Solicite uno nuevo",
            {},
        ),
    },
    summary="Activar la cuenta con el enlace del correo",
    description=(
        "Es el enlace que llega al correo. El token identifica la cuenta: si está vigente y no se "
        "ha usado, la cuenta pasa a ACTIVE y ya puede iniciar sesión. Cada token sirve una sola vez."
    ),
)
def verificar_correo(token: str = Query(..., description="Token recibido en el enlace del correo")):
    try:
        usuario = servicio.verificar(token)
    except ErrorDominio as error:
        raise a_http(error) from error
    return RespuestaApi(message="Cuenta activada correctamente. Ya puede iniciar sesión", data=usuario)


@router.post(
    "/usuarios/reenviar-verificacion",
    tags=["Usuarios (HU-01)"],
    response_model=RespuestaApi[ReenvioResponse],
    responses={
        400: _error("El correo no tiene un formato válido", "El correo no tiene un formato válido", {"correo": "laura"}),
        404: _error(
            "No hay una cuenta con ese correo",
            "No existe una cuenta registrada con ese correo",
            {"correo": "laura.gomez@gmail.com"},
        ),
        409: _error("La cuenta ya está activada", "La cuenta ya está activada", {"correo": "laura.gomez@gmail.com"}),
        429: _error(
            "Se pidió otro correo hace menos de 60 segundos",
            "Espere antes de solicitar otro correo de verificación",
            {"segundos_restantes": 42},
        ),
        503: _ERROR_503,
    },
    summary="Reenviar el enlace de activación",
    description=(
        "Extra a la HU-01: envía un enlace nuevo a una cuenta en PENDING_VERIFICATION, por si el "
        "correo no llegó o el enlace venció. Los enlaces anteriores dejan de servir. Hay que "
        "esperar 60 segundos entre solicitudes."
    ),
)
def reenviar_verificacion(datos: SolicitudReenvio):
    try:
        resultado = servicio.reenviar_verificacion(datos.correo)
    except ErrorDominio as error:
        raise a_http(error) from error
    return RespuestaApi(message="Se envió un nuevo enlace de activación a su correo", data=resultado)


@router.post(
    "/usuarios/recuperar-contrasena",
    tags=["Usuarios (HU-03)"],
    response_model=RespuestaApi[RecuperacionResponse],
    responses={
        400: _error("El correo no tiene un formato válido", "El correo no tiene un formato válido", {"correo": "laura"}),
        503: _ERROR_503,
    },
    summary="Solicitar un código para recuperar la contraseña",
    description=(
        "Envía al correo un código de 6 dígitos de un solo uso que vence en 15 minutos (API-E03). "
        "Solo las cuentas ACTIVE reciben el código, y cada solicitud nueva deja sin efecto los "
        "códigos anteriores. Para no revelar qué correos están registrados, la respuesta es la "
        "misma exista o no la cuenta; si se pide otro código antes de 60 segundos no se envía "
        "nada. Si el correo no se puede enviar, el código no se guarda (503)."
    ),
)
def solicitar_codigo_recuperacion(datos: SolicitudRecuperacion):
    try:
        resultado = servicio_recuperacion.solicitar_codigo(datos.correo)
    except ErrorDominio as error:
        raise a_http(error) from error
    return RespuestaApi(
        message="Si el correo está registrado, recibirá un código para restablecer la contraseña",
        data=resultado,
    )


@router.put(
    "/usuarios/recuperar-contrasena",
    tags=["Usuarios (HU-03)"],
    response_model=RespuestaApi[ContrasenaActualizadaResponse],
    responses={
        400: _error(
            "El código no existe, ya se usó, venció o se superaron los 5 intentos; o la contraseña no cumple RN-02",
            MENSAJE_CODIGO_INVALIDO,
            {"correo": "laura.gomez@gmail.com"},
        ),
    },
    summary="Cambiar la contraseña con el código del correo",
    description=(
        "Recibe el correo, el código de 6 dígitos y la contraseña nueva, que debe tener mínimo "
        "8 caracteres, una mayúscula y un número (RN-02). Solo sirve el último código enviado, "
        "dentro de sus 15 minutos y una sola vez; al quinto código erróneo queda invalidado. "
        "La contraseña se guarda con hash bcrypt y se quita el bloqueo por intentos fallidos "
        "del login (RN-03)."
    ),
)
def cambiar_contrasena(datos: CambioContrasena):
    try:
        resultado = servicio_recuperacion.cambiar_contrasena(datos)
    except ErrorDominio as error:
        raise a_http(error) from error
    return RespuestaApi(message="Contraseña actualizada correctamente", data=resultado)
