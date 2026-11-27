"""Dominio de Servicio (mínimo necesario para HU-23, HU-36 y HU-37).

La creación y edición de servicios corresponde a HU-21 y su asociación a sedes a HU-22;
aquí solo está lo que necesitan los horarios y las reservas para consultar un servicio.

Reglas:
- RN-11: la duración de un servicio es múltiplo de 15 minutos.
- RN-12: un servicio solo se ofrece en sedes de su misma empresa.
"""

from app.domain.estados import EstadoRegistro


def esta_activo(estado: EstadoRegistro) -> bool:
    return estado == EstadoRegistro.ACTIVE


def se_ofrece_en(servicio: dict, sede_id: int) -> bool:
    return sede_id in servicio.get("sedes", [])
