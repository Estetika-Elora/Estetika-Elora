"""Dominio de Sede (HU-16): schemas de entrada y salida con sus validaciones."""

import re

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.domain.estados import EstadoRegistro
from app.domain.validaciones import limpiar_texto

_PATRON_TELEFONO = re.compile(r"^\d{10}$")


def _validar_telefono(valor: str) -> str:
    """Teléfono colombiano de 10 dígitos (celular o fijo con indicativo 60X)."""
    limpio = re.sub(r"[\s\-()]", "", valor)
    if not _PATRON_TELEFONO.match(limpio):
        raise ValueError("El teléfono debe tener 10 dígitos")
    return limpio


class SedeCreate(BaseModel):
    """Datos para registrar una sede."""

    nombre: str
    ciudad: str
    direccion: str
    telefono: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nombre": "Sede Cabecera",
                "ciudad": "Bucaramanga",
                "direccion": "Carrera 33 # 48-20",
                "telefono": "6076345120",
            }
        }
    )

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, valor: str) -> str:
        return limpiar_texto(valor, "nombre", 3, 100)

    @field_validator("ciudad")
    @classmethod
    def validar_ciudad(cls, valor: str) -> str:
        return limpiar_texto(valor, "ciudad", 2, 60)

    @field_validator("direccion")
    @classmethod
    def validar_direccion(cls, valor: str) -> str:
        return limpiar_texto(valor, "direccion", 5, 150)

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, valor: str) -> str:
        return _validar_telefono(valor)


class SedeUpdate(BaseModel):
    """Datos para editar una sede. Todos son opcionales, pero se exige al menos uno."""

    nombre: str | None = None
    ciudad: str | None = None
    direccion: str | None = None
    telefono: str | None = None

    model_config = ConfigDict(json_schema_extra={"example": {"telefono": "6076345199"}})

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, valor: str | None) -> str | None:
        return None if valor is None else limpiar_texto(valor, "nombre", 3, 100)

    @field_validator("ciudad")
    @classmethod
    def validar_ciudad(cls, valor: str | None) -> str | None:
        return None if valor is None else limpiar_texto(valor, "ciudad", 2, 60)

    @field_validator("direccion")
    @classmethod
    def validar_direccion(cls, valor: str | None) -> str | None:
        return None if valor is None else limpiar_texto(valor, "direccion", 5, 150)

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, valor: str | None) -> str | None:
        return None if valor is None else _validar_telefono(valor)

    @model_validator(mode="after")
    def exigir_algun_campo(self) -> "SedeUpdate":
        if not self.model_dump(exclude_none=True):
            raise ValueError("Debe enviar al menos un campo para actualizar")
        return self


class SedeResponse(BaseModel):
    """Sede tal como se devuelve al cliente."""

    sede_id: int
    empresa_id: int
    nombre: str
    ciudad: str
    direccion: str
    telefono: str
    latitud: float
    longitud: float
    estado: EstadoRegistro

    model_config = ConfigDict(from_attributes=True)
