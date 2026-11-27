"""Validaciones reutilizables por los schemas del dominio."""

import re

_PATRON_TELEFONO = re.compile(r"^\d{10}$")


def validar_telefono(valor: str) -> str:
    """Teléfono colombiano de 10 dígitos (celular o fijo con indicativo 60X)."""
    limpio = re.sub(r"[\s\-()]", "", valor)
    if not _PATRON_TELEFONO.match(limpio):
        raise ValueError("El teléfono debe tener 10 dígitos")
    return limpio


def limpiar_texto(valor: str, campo: str, minimo: int, maximo: int) -> str:
    """Quita espacios sobrantes y valida la longitud del texto.

    Lanza ValueError con un mensaje en español; Pydantic lo convierte en error de validación.
    """
    limpio = " ".join(valor.split())
    if len(limpio) < minimo:
        raise ValueError(f"El campo {campo} debe tener al menos {minimo} caracteres")
    if len(limpio) > maximo:
        raise ValueError(f"El campo {campo} no puede superar {maximo} caracteres")
    return limpio

def validar_nit(valor: str, campo: str) -> str:
    """Quita espacios sobrantes y valida los campos del texto".

    Lanza ValueError con un mensaje en español; Pydantic lo convierte en error de validación.
    """
    limpio = " ".join(valor.split())
    if len(limpio) != 9:
        raise ValueError(f"El campo {campo} debe tener 9 caracteres")
    return limpio
