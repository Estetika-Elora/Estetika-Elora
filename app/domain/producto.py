"""Dominio de Producto (HU-31, HU-32): schemas de entrada y salida con sus validaciones."""

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.domain.estados import EstadoRegistro
from app.domain.validaciones import limpiar_texto

UMBRAL_STOCK_BAJO = 5


def _validar_precio(valor: int) -> int:
    if valor <= 0:
        raise ValueError("El precio debe ser mayor que cero")
    return valor


def _validar_stock(valor: int) -> int:
    """RN-16: el stock nunca puede ser negativo."""
    if valor < 0:
        raise ValueError("El stock no puede ser negativo")
    return valor


class ProductoCreate(BaseModel):
    """Datos para publicar un producto. El precio va en pesos colombianos, sin decimales."""

    nombre: str
    categoria: str
    descripcion: str
    precio: int
    stock: int

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, valor: str) -> str:
        return limpiar_texto(valor, "nombre", 3, 120)

    @field_validator("categoria")
    @classmethod
    def validar_categoria(cls, valor: str) -> str:
        return limpiar_texto(valor, "categoria", 3, 60)

    @field_validator("descripcion")
    @classmethod
    def validar_descripcion(cls, valor: str) -> str:
        return limpiar_texto(valor, "descripcion", 1, 1000)

    @field_validator("precio")
    @classmethod
    def validar_precio(cls, valor: int) -> int:
        return _validar_precio(valor)

    @field_validator("stock")
    @classmethod
    def validar_stock(cls, valor: int) -> int:
        return _validar_stock(valor)


class ProductoUpdate(BaseModel):
    """Datos para editar un producto. Todos son opcionales.

    Puede llegar sin campos si en la petición solo vienen imágenes nuevas; el servicio
    exige que llegue al menos un campo o una imagen.
    """

    nombre: str | None = None
    categoria: str | None = None
    descripcion: str | None = None
    precio: int | None = None
    stock: int | None = None

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, valor: str | None) -> str | None:
        return None if valor is None else limpiar_texto(valor, "nombre", 3, 120)

    @field_validator("categoria")
    @classmethod
    def validar_categoria(cls, valor: str | None) -> str | None:
        return None if valor is None else limpiar_texto(valor, "categoria", 3, 60)

    @field_validator("descripcion")
    @classmethod
    def validar_descripcion(cls, valor: str | None) -> str | None:
        return None if valor is None else limpiar_texto(valor, "descripcion", 1, 1000)

    @field_validator("precio")
    @classmethod
    def validar_precio(cls, valor: int | None) -> int | None:
        return None if valor is None else _validar_precio(valor)

    @field_validator("stock")
    @classmethod
    def validar_stock(cls, valor: int | None) -> int | None:
        return None if valor is None else _validar_stock(valor)


class ProductoResponse(BaseModel):
    """Producto tal como se devuelve al cliente."""

    producto_id: int
    empresa_id: int
    nombre: str
    categoria: str
    descripcion: str
    precio: int
    stock: int
    imagenes: list[str]
    estado: EstadoRegistro

    model_config = ConfigDict(from_attributes=True)


class StockUpdate(BaseModel):
    """Nueva cantidad de stock o ajuste (+ o −) sobre el actual. Se envía solo uno de los dos."""

    cantidad: int | None = None
    ajuste: int | None = None

    @field_validator("cantidad")
    @classmethod
    def validar_cantidad(cls, valor: int | None) -> int | None:
        return None if valor is None else _validar_stock(valor)

    @model_validator(mode="after")
    def validar_un_solo_campo(self) -> "StockUpdate":
        if (self.cantidad is None) == (self.ajuste is None):
            raise ValueError("Debe enviar solo uno de los campos cantidad o ajuste")
        return self


class StockResponse(BaseModel):
    """Resultado de actualizar el stock de un producto (RN-20: alerta de stock bajo)."""

    producto_id: int
    nombre: str
    stock_anterior: int
    stock_actual: int
    alerta_stock_bajo: bool
