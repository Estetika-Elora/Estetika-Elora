"""Dominio del horario de atención de una sede (HU-17): días, franjas y reglas.

Reglas:
- RN-13: los usuarios solo reservan dentro del horario de atención de la sede.
- Cada día tiene una sola franja (apertura y cierre) y no se puede repetir.
- Las horas van en formato HH:MM y en intervalos de 15 minutos, igual que la duración
  de los servicios (HU-21), para que los bloques de HU-23 cuadren.
- La apertura debe ser menor que el cierre: se valida en el servicio para devolver
  el día con el error en `data`.
- Un día que no aparece en el horario se considera cerrado.
"""

import re
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator

INTERVALO_MINUTOS = 15
_PATRON_HORA = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


class DiaSemana(str, Enum):
    """Los valores siguen el contrato JSON de la HU ("dia": "lunes")."""

    LUNES = "lunes"
    MARTES = "martes"
    MIERCOLES = "miercoles"
    JUEVES = "jueves"
    VIERNES = "viernes"
    SABADO = "sabado"
    DOMINGO = "domingo"


ORDEN_DIAS = list(DiaSemana)


def a_minutos(hora: str) -> int:
    """Convierte "HH:MM" en minutos desde la medianoche."""
    horas, minutos = hora.split(":")
    return int(horas) * 60 + int(minutos)


def validar_hora(valor: str) -> str:
    limpio = valor.strip()
    coincidencia = _PATRON_HORA.match(limpio)
    if coincidencia is None:
        raise ValueError("La hora debe tener el formato HH:MM de 24 horas (por ejemplo 08:00)")
    if int(coincidencia.group(2)) % INTERVALO_MINUTOS != 0:
        raise ValueError(
            f"La hora debe ir en intervalos de {INTERVALO_MINUTOS} minutos (por ejemplo 08:00 u 08:15)"
        )
    return limpio


def apertura_menor_que_cierre(apertura: str, cierre: str) -> bool:
    return a_minutos(apertura) < a_minutos(cierre)


class FranjaHorario(BaseModel):
    """Horario de un día: hora de apertura y hora de cierre."""

    dia: DiaSemana
    apertura: str
    cierre: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator("apertura", "cierre")
    @classmethod
    def validar_formato_hora(cls, valor: str) -> str:
        return validar_hora(valor)


class HorarioUpdate(BaseModel):
    """Horario completo de la sede. Reemplaza al anterior; los días no enviados quedan cerrados."""

    horario: list[FranjaHorario]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "horario": [
                    {"dia": "lunes", "apertura": "08:00", "cierre": "18:00"},
                    {"dia": "sabado", "apertura": "08:00", "cierre": "13:00"},
                ]
            }
        }
    )

    @field_validator("horario")
    @classmethod
    def validar_dias(cls, valor: list[FranjaHorario]) -> list[FranjaHorario]:
        if not valor:
            raise ValueError("Debe enviar al menos un día de atención")
        vistos: set[DiaSemana] = set()
        for franja in valor:
            if franja.dia in vistos:
                raise ValueError(f"El día {franja.dia.value} está repetido en el horario")
            vistos.add(franja.dia)
        return sorted(valor, key=lambda franja: ORDEN_DIAS.index(franja.dia))


class HorarioResponse(BaseModel):
    """Horario de atención de una sede tal como se devuelve al cliente."""

    sede_id: int
    horario: list[FranjaHorario]
    disponibilidad_regenerada: bool | None = None
