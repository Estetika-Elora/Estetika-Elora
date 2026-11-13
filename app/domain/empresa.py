"""Dominio de Empresa (mínimo necesario para HU-16 y HU-31).

El registro completo de empresas corresponde a HU-11; aquí solo está lo que necesitan
sedes y productos para aplicar la regla RN-07.
"""

from enum import Enum


class EstadoEmpresa(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


def puede_publicar(estado: EstadoEmpresa) -> bool:
    """RN-07: solo una empresa aprobada puede publicar sedes, servicios y productos."""
    return estado == EstadoEmpresa.APPROVED
