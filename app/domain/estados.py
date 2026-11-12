"""Estados comunes a las entidades del catálogo.

Convención del proyecto: los valores de los enums van en inglés y en mayúscula.
"""

from enum import Enum


class EstadoRegistro(str, Enum):
    """Estado de las entidades que se activan o desactivan (sede, producto, servicio)."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
