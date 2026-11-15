"""Dominio de Usuario (HU-01): schemas de entrada y salida, estados, roles y reglas.

Reglas de negocio:
- RN-01: el correo es único en la plataforma (se valida en el servicio).
- RN-02: la contraseña tiene mínimo 8 caracteres, una mayúscula y un número.
"""

import re
from enum import Enum

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, ConfigDict, field_validator

from app.domain.validaciones import limpiar_texto, validar_telefono


class EstadoCuenta(str, Enum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class Rol(str, Enum):
    """Roles de la plataforma (Parcial 1, PRO-06).

    Los valores siguen el contrato JSON de las HU ("rol": "usuario", "administrador_empresa").
    """

    USUARIO = "usuario"
    ADMINISTRADOR_SEDE = "administrador_sede"
    ADMINISTRADOR_EMPRESA = "administrador_empresa"
    ADMINISTRADOR_PLATAFORMA = "administrador_plataforma"


CONTRASENA_LONGITUD_MINIMA = 8
CONTRASENA_LONGITUD_MAXIMA = 64
MENSAJE_POLITICA_CONTRASENA = (
    "La contraseña debe tener mínimo 8 caracteres, una letra mayúscula y un número"
)


def validar_contrasena(valor: str) -> str:
    """RN-02: mínimo 8 caracteres, una mayúscula y un número. No se recortan espacios."""
    if (
        len(valor) < CONTRASENA_LONGITUD_MINIMA
        or not re.search(r"[A-ZÁÉÍÓÚÑ]", valor)
        or not re.search(r"\d", valor)
    ):
        raise ValueError(MENSAJE_POLITICA_CONTRASENA)
    if len(valor) > CONTRASENA_LONGITUD_MAXIMA:
        raise ValueError(f"La contraseña no puede superar {CONTRASENA_LONGITUD_MAXIMA} caracteres")
    return valor


def normalizar_correo(valor: str) -> str:
    """Valida el formato del correo y lo devuelve en minúsculas (RN-01 compara sin mayúsculas)."""
    try:
        resultado = validate_email(valor.strip(), check_deliverability=False)
    except EmailNotValidError as error:
        raise ValueError("El correo no tiene un formato válido") from error
    return resultado.normalized.lower()


class UsuarioCreate(BaseModel):
    """Datos para registrarse. El rol no se recibe: todo registro queda como «usuario»."""

    nombre: str
    correo: str
    telefono: str
    contrasena: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nombre": "Laura Gómez",
                "correo": "laura.gomez@gmail.com",
                "telefono": "3157784512",
                "contrasena": "Clave2026",
            }
        }
    )

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, valor: str) -> str:
        return limpiar_texto(valor, "nombre", 3, 100)

    @field_validator("correo")
    @classmethod
    def validar_correo(cls, valor: str) -> str:
        return normalizar_correo(valor)

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, valor: str) -> str:
        return validar_telefono(valor)

    @field_validator("contrasena")
    @classmethod
    def validar_contrasena(cls, valor: str) -> str:
        return validar_contrasena(valor)


class SolicitudReenvio(BaseModel):
    """Correo de la cuenta pendiente a la que se le reenvía el enlace de activación."""

    correo: str

    model_config = ConfigDict(json_schema_extra={"example": {"correo": "laura.gomez@gmail.com"}})

    @field_validator("correo")
    @classmethod
    def validar_correo(cls, valor: str) -> str:
        return normalizar_correo(valor)


class UsuarioResponse(BaseModel):
    """Usuario tal como se devuelve al cliente. Nunca incluye la contraseña."""

    usuario_id: int
    nombre: str
    correo: str
    telefono: str
    estado: EstadoCuenta

    model_config = ConfigDict(from_attributes=True)


class ReenvioResponse(BaseModel):
    correo: str
    vigencia_horas: int
