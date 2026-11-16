"""Dominio de los horarios disponibles (HU-23): rango de fechas y cálculo de bloques.

Reglas:
- RN-13: los bloques solo se generan dentro del horario de atención de la sede y excluyen
  los horarios ocupados por reservas y los bloqueos de agenda.
- Cada bloque dura lo mismo que el servicio y empieza donde termina el anterior. Un bloque
  que terminaría después del cierre no se genera.
- Para la fecha de hoy no se generan bloques que ya empezaron.
- El rango manual va de hoy en adelante y no supera 90 días. La regeneración automática
  (al cambiar el horario de la sede, HU-17) cubre los próximos 30 días.
"""

import re
from datetime import date, datetime, timedelta

from pydantic import BaseModel, ConfigDict, field_validator

from app.domain.errores import DatosInvalidos
from app.domain.horario import ORDEN_DIAS, a_minutos

MAXIMO_DIAS_RANGO = 90
DIAS_REGENERACION = 30
MENSAJE_FORMATO_FECHA = "Formato de fecha no válido. Debe ser YYYY-MM-DD"
_PATRON_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def a_hora(minutos: int) -> str:
    """Convierte minutos desde la medianoche en "HH:MM"."""
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def leer_fecha(valor: object) -> date:
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str) and _PATRON_FECHA.match(valor.strip()):
        try:
            return date.fromisoformat(valor.strip())
        except ValueError:
            pass
    raise ValueError(MENSAJE_FORMATO_FECHA)


def validar_rango(desde: date, hasta: date, hoy: date) -> None:
    data = {"desde": desde.isoformat(), "hasta": hasta.isoformat()}
    if desde < hoy:
        raise DatosInvalidos("La fecha desde no puede ser anterior a hoy", data)
    if hasta < desde:
        raise DatosInvalidos("La fecha hasta debe ser igual o posterior a la fecha desde", data)
    if (hasta - desde).days + 1 > MAXIMO_DIAS_RANGO:
        raise DatosInvalidos(f"El rango de fechas no puede superar {MAXIMO_DIAS_RANGO} días", data)


def rango_regeneracion(hoy: date) -> tuple[date, date]:
    return hoy, hoy + timedelta(days=DIAS_REGENERACION - 1)


def generar_bloques(
    horario: list[dict],
    desde: date,
    hasta: date,
    duracion_min: int,
    ocupados: list[tuple[date, int, int]],
    ahora: datetime,
) -> list[dict]:
    """Calcula los bloques libres de cada fecha del rango.

    `horario` es la lista de franjas de la sede ({dia, apertura, cierre}).
    `ocupados` son intervalos (fecha, inicio, fin) en minutos: reservas y bloqueos.
    Devuelve una lista de {"fecha": date, "hora": "HH:MM"} en orden.
    """
    franjas = {franja["dia"]: franja for franja in horario}
    bloques: list[dict] = []
    fecha = desde
    while fecha <= hasta:
        franja = franjas.get(ORDEN_DIAS[fecha.weekday()].value)
        if franja is not None:
            inicio = a_minutos(franja["apertura"])
            cierre = a_minutos(franja["cierre"])
            ocupados_dia = [(i, f) for d, i, f in ocupados if d == fecha]
            while inicio + duracion_min <= cierre:
                fin = inicio + duracion_min
                ya_paso = datetime.combine(fecha, datetime.min.time()) + timedelta(minutes=inicio) < ahora
                choca = any(inicio < f and i < fin for i, f in ocupados_dia)
                if not ya_paso and not choca:
                    bloques.append({"fecha": fecha, "hora": a_hora(inicio)})
                inicio = fin
        fecha += timedelta(days=1)
    return bloques


class GeneracionRequest(BaseModel):
    """Rango de fechas (incluidas ambas) para generar los horarios de un servicio."""

    desde: date
    hasta: date

    model_config = ConfigDict(
        json_schema_extra={"example": {"desde": "2026-11-16", "hasta": "2026-11-22"}}
    )

    @field_validator("desde", "hasta", mode="before")
    @classmethod
    def validar_formato_fecha(cls, valor: object) -> date:
        return leer_fecha(valor)


class GeneracionResponse(BaseModel):
    sede_id: int
    servicio_id: int
    desde: date
    hasta: date
    duracion_min: int
    bloques_generados: int
