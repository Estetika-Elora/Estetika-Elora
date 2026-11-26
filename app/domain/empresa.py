"""Dominio de Empresa (HU-11, HU-14, HU-16, HU-19 y HU-31).

Define los estados, las reglas de publicación y los contratos de entrada/salida
que utiliza el módulo de empresas.
"""

import re
from datetime import date
from enum import Enum

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, ConfigDict, field_validator

from app.domain.validaciones import limpiar_texto, validar_telefono

HORAS_MINIMAS_ANTELACION_MIN = 1
HORAS_MINIMAS_ANTELACION_MAX = 72
HORAS_MINIMAS_ANTELACION_DEFECTO = 24


class EstadoEmpresa(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


def puede_publicar(estado: EstadoEmpresa) -> bool:
    """RN-07: solo una empresa aprobada puede publicar sedes, servicios y productos."""
    return estado == EstadoEmpresa.APPROVED


def normalizar_correo_empresa(
    valor: str, mensaje: str = "El correo del representante no tiene un formato válido"
) -> str:
    """Valida un correo de la empresa y lo normaliza en minúsculas."""
    try:
        resultado = validate_email(valor.strip(), check_deliverability=False)
    except EmailNotValidError as error:
        raise ValueError(mensaje) from error
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


class EmpresaUpdate(BaseModel):
    """Datos para editar el perfil comercial de una empresa (HU-14). Todos son opcionales.

    `nit` y `razon_social` no se pueden modificar: se reciben solo para que el servicio
    rechace el intento de cambiarlos.
    """

    nit: str | None = None
    razon_social: str | None = None
    descripcion: str | None = None
    telefono: str | None = None
    correo_contacto: str | None = None

    @field_validator("descripcion")
    @classmethod
    def validar_descripcion(cls, valor: str | None) -> str | None:
        return None if valor is None else limpiar_texto(valor, "descripcion", 10, 500)

    @field_validator("telefono")
    @classmethod
    def validar_telefono_empresa(cls, valor: str | None) -> str | None:
        return None if valor is None else validar_telefono(valor)

    @field_validator("correo_contacto")
    @classmethod
    def validar_correo_contacto(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return normalizar_correo_empresa(valor, "El correo de contacto no tiene un formato válido")


class EmpresaPerfilResponse(BaseModel):
    """Perfil comercial de la empresa devuelto al editarla (HU-14)."""

    empresa_id: int
    razon_social: str
    descripcion: str | None = None
    telefono: str | None = None
    correo_contacto: str | None = None
    logo_url: str | None = None


class PoliticaCancelacionUpdate(BaseModel):
    """Horas mínimas de antelación para cancelar o reprogramar una reserva (RN-24)."""

    horas_minimas_antelacion: int

    model_config = ConfigDict(json_schema_extra={"example": {"horas_minimas_antelacion": 24}})

    @field_validator("horas_minimas_antelacion")
    @classmethod
    def validar_horas(cls, valor: int) -> int:
        if not HORAS_MINIMAS_ANTELACION_MIN <= valor <= HORAS_MINIMAS_ANTELACION_MAX:
            raise ValueError(
                f"Las horas mínimas deben estar entre {HORAS_MINIMAS_ANTELACION_MIN} "
                f"y {HORAS_MINIMAS_ANTELACION_MAX}"
            )
        return valor


class PoliticaCancelacionResponse(BaseModel):
    """Política de cancelación vigente de una empresa."""

    empresa_id: int
    horas_minimas_antelacion: int
    vigente_desde: date | None
