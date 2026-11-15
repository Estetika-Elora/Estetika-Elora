"""Endpoints de autenticación (HU-02). Solo llaman al servicio y convierten errores en HTTP."""

import os

from fastapi import APIRouter

from app.api.respuestas import RespuestaApi, RespuestaError, a_http
from app.domain.auth import LoginRequest, LoginResponse
from app.domain.errores import ErrorDominio
from app.repository.usuario_repository import usuario_repository
from app.service.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación (HU-02)"])


def _secreto() -> str:
    secreto = os.getenv("SECRET_KEY", "").strip()
    if not secreto:
        raise RuntimeError("Falta la variable SECRET_KEY en el archivo .env")
    return secreto


def _minutos_token() -> int:
    try:
        return int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    except ValueError:
        return 60


servicio = AuthService(usuario_repository, _secreto(), _minutos_token())


def _error(descripcion: str, mensaje: str, data: dict) -> dict:
    return {
        "model": RespuestaError,
        "description": descripcion,
        "content": {"application/json": {"example": {"message": mensaje, "data": data, "success": False}}},
    }


@router.post(
    "/login",
    response_model=RespuestaApi[LoginResponse],
    responses={
        400: _error("El correo no tiene formato válido o falta un campo", "El correo no tiene un formato válido", {"correo": "laura"}),
        401: _error("Correo o contraseña incorrectos", "Correo o contraseña incorrectos", {"intentos_restantes": 3}),
        403: _error(
            "La cuenta no está activa (pendiente de verificación o suspendida)",
            "Debe activar su cuenta antes de iniciar sesión",
            {},
        ),
        423: _error(
            "Cuenta bloqueada 15 minutos por 5 intentos fallidos seguidos (RN-03)",
            "Se superaron los 5 intentos fallidos. La cuenta queda bloqueada 15 minutos",
            {"minutos_restantes": 15},
        ),
    },
    summary="Iniciar sesión de forma segura",
    description=(
        "Valida el correo y la contraseña de una cuenta ACTIVE y entrega un token JWT con el id y "
        "el rol del usuario, válido por 60 minutos (`expira_en` en segundos). Cada intento "
        "fallido se registra; al quinto seguido la cuenta se bloquea 15 minutos (RN-03) y durante "
        "ese tiempo no se puede ingresar ni con la contraseña correcta."
    ),
)
def iniciar_sesion(datos: LoginRequest):
    try:
        sesion = servicio.iniciar_sesion(datos)
    except ErrorDominio as error:
        raise a_http(error) from error
    return RespuestaApi(message="Inicio de sesión exitoso", data=sesion)
