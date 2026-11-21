"""Dominio de Empresa (HU-11, HU-16 y HU-31).

Define los estados, las reglas de publicación y los contratos de entrada/salida
que utiliza el módulo de empresas.
"""

import re
from enum import Enum

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, ConfigDict, field_validator

from app.domain.validaciones import limpiar_texto


class EstadoEmpresa(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


def puede_publicar(estado: EstadoEmpresa) -> bool:
    """RN-07: solo una empresa aprobada puede publicar sedes, servicios y productos."""
    return estado == EstadoEmpresa.APPROVED


def normalizar_correo_empresa(valor: str) -> str:
    """Valida el correo del representante y lo normaliza en minúsculas."""
    try:
        resultado = validate_email(valor.strip(), check_deliverability=False)
    except EmailNotValidError as error:
        raise ValueError("El correo del representante no tiene un formato válido") from error
    return resultado.normalized.lower()


class EmpresaCreate(BaseModel):
    """Información requerida para solicitar el registro de una empresa (HU-11)."""

    nit: str
    razon_social: str
    categoria: str
    representante: str
    correo_representante: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nit": "901456789-3",
                "razon_social": "Spa Bella Piel S.A.S.",
                "categoria": "Spa y estética facial",
                "representante": "Laura Gómez",
                "correo_representante": "laura@gmail.com",
            }
        }
    )

    @field_validator("nit")
    @classmethod
    def validar_nit_empresa(cls, valor: str) -> str:
        nit = valor.strip()
        # NIT colombiano según el formato solicitado en HU-11: 9 dígitos + guion + DV.
        if not re.fullmatch(r"\d{9}-\d", nit):
            raise ValueError("El NIT debe tener el formato de 9 dígitos, guion y dígito de verificación (ej. 901456789-3)")
        return nit

    @field_validator("razon_social")
    @classmethod
    def validar_razon_social(cls, valor: str) -> str:
        return limpiar_texto(valor, "razon_social", 3, 120)

    @field_validator("categoria")
    @classmethod
    def validar_categoria(cls, valor: str) -> str:
        return limpiar_texto(valor, "categoria", 3, 60)

    @field_validator("representante")
    @classmethod
    def validar_representante(cls, valor: str) -> str:
        return limpiar_texto(valor, "representante", 3, 120)

    @field_validator("correo_representante")
    @classmethod
    def validar_correo_representante(cls, valor: str) -> str:
        return normalizar_correo_empresa(valor)


class EmpresaResponse(BaseModel):
    """Datos públicos devueltos al registrar o consultar una empresa."""

    empresa_id: int
    nit: str
    razon_social: str
    categoria: str
    representante: str
    estado: EstadoEmpresa

    model_config = ConfigDict(from_attributes=True)
