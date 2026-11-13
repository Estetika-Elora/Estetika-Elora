"""Formato estándar de respuesta de la API y conversión de errores a HTTP.

Toda respuesta, de éxito o de error, tiene la forma:
{"message": str, "data": ..., "success": bool}
"""

from typing import Any, Generic, TypeVar

from fastapi import HTTPException, status
from pydantic import BaseModel

from app.domain.errores import (
    DatosInvalidos,
    ErrorDominio,
    OperacionNoPermitida,
    RecursoNoEncontrado,
    ServicioExternoNoDisponible,
)

T = TypeVar("T")


class RespuestaApi(BaseModel, Generic[T]):
    message: str
    data: T
    success: bool = True


class RespuestaError(BaseModel):
    message: str
    data: dict[str, Any]
    success: bool = False


RESPUESTAS_ERROR: dict[int | str, dict[str, Any]] = {
    400: {"model": RespuestaError, "description": "Datos inválidos"},
    403: {"model": RespuestaError, "description": "La empresa no está aprobada (RN-07)"},
    404: {"model": RespuestaError, "description": "La empresa o el recurso no existe"},
    503: {"model": RespuestaError, "description": "Servicio externo no disponible"},
}

_CODIGOS_HTTP = {
    DatosInvalidos: status.HTTP_400_BAD_REQUEST,
    OperacionNoPermitida: status.HTTP_403_FORBIDDEN,
    RecursoNoEncontrado: status.HTTP_404_NOT_FOUND,
    ServicioExternoNoDisponible: status.HTTP_503_SERVICE_UNAVAILABLE,
}


def cuerpo_error(mensaje: str, data: dict | None = None) -> dict:
    return {"message": mensaje, "data": data or {}, "success": False}


def a_http(error: ErrorDominio) -> HTTPException:
    """Convierte un error del dominio en HTTPException con el formato estándar."""
    codigo = _CODIGOS_HTTP.get(type(error), status.HTTP_400_BAD_REQUEST)
    return HTTPException(status_code=codigo, detail=cuerpo_error(error.mensaje, error.data))


def _valor_serializable(valor: Any) -> Any:
    return valor if isinstance(valor, (str, int, float, bool)) or valor is None else None


def traducir_errores_validacion(errores: list[dict]) -> dict:
    """Convierte los errores de Pydantic/FastAPI en el formato estándar, en español.

    El mensaje es el del primer error; `data` trae cada campo inválido con el valor recibido.
    """
    data: dict[str, Any] = {}
    mensajes: list[str] = []
    for error in errores:
        ubicacion = [str(p) for p in error.get("loc", ()) if p not in ("body", "query", "path", "form")]
        campo = ubicacion[0] if ubicacion else None
        tipo = error.get("type", "")

        if tipo == "value_error":
            mensaje = str(error.get("msg", "")).removeprefix("Value error, ")
        elif tipo == "missing":
            mensaje = f"El campo {campo} es obligatorio"
        elif tipo in ("int_parsing", "int_type", "int_from_float"):
            mensaje = f"El campo {campo} debe ser un número entero"
        elif tipo in ("float_parsing", "float_type"):
            mensaje = f"El campo {campo} debe ser numérico"
        elif tipo == "json_invalid":
            mensaje = "El cuerpo de la petición no es un JSON válido"
        else:
            mensaje = f"El campo {campo} no es válido" if campo else "La petición no es válida"

        mensajes.append(mensaje)
        if campo:
            data[campo] = None if tipo == "missing" else _valor_serializable(error.get("input"))

    return cuerpo_error(mensajes[0] if mensajes else "La petición no es válida", data)


def error_validacion(errores: list[dict]) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=traducir_errores_validacion(errores))
