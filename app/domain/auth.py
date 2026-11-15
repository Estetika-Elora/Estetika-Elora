"""Dominio de Autenticación (HU-02): schemas del login y regla de bloqueo.

RN-03: después de 5 intentos fallidos seguidos la cuenta se bloquea durante 15 minutos.
En el login la contraseña no se valida contra la política RN-02; solo se compara con el hash.
"""

from pydantic import BaseModel, ConfigDict, field_validator

from app.domain.usuario import Rol, normalizar_correo

MAXIMO_INTENTOS_FALLIDOS = 5
MINUTOS_BLOQUEO = 15


class LoginRequest(BaseModel):
    correo: str
    contrasena: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"correo": "laura.gomez@gmail.com", "contrasena": "Clave2026"}}
    )

    @field_validator("correo")
    @classmethod
    def validar_correo(cls, valor: str) -> str:
        return normalizar_correo(valor)

    @field_validator("contrasena")
    @classmethod
    def validar_contrasena(cls, valor: str) -> str:
        if not valor:
            raise ValueError("El campo contrasena es obligatorio")
        return valor


class LoginResponse(BaseModel):
    usuario_id: int
    nombre: str
    rol: Rol
    token: str
    expira_en: int
