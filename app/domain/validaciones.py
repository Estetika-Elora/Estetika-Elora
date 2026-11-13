"""Validaciones reutilizables por los schemas del dominio."""


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
