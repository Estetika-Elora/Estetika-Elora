"""Dominio de Reserva (MOD-05): horarios libres (HU-36), creación de reservas (HU-37),
historial del usuario (HU-05) y cierre de la reserva (HU-40).

Reglas:
- RN-13: solo se ofrecen los horarios que generó el catálogo (HU-23), que ya están dentro
  del horario de atención de la sede y sin bloqueos de agenda.
- RN-21: un mismo horario de una sede no puede tener dos reservas confirmadas para el mismo
  servicio; un horario reservado no se muestra como libre.
- RN-04: solo una cuenta activa puede reservar; una cuenta suspendida no.
- No se muestran ni se reservan horarios que ya empezaron.
- RN-23 (bloqueo temporal de 10 minutos mientras se paga) no aplica todavía: los pagos están
  fuera del alcance y la reserva nace CONFIRMED, como pide la HU-37.
- HU-05: el historial de un usuario se ordena de la reserva más reciente a la más antigua
  y se puede filtrar por un rango de fechas (ambos extremos incluidos).
- RN-25: una reserva solo se cierra (COMPLETED o NO_SHOW) después de la fecha y hora de la
  cita, y solo si sigue CONFIRMED. La reseña queda habilitada cuando la reserva está
  COMPLETED (API-I21); con NO_SHOW no.
"""

from datetime import date, datetime, timedelta
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator

from app.domain.disponibilidad import MENSAJE_FORMATO_FECHA, leer_fecha
from app.domain.errores import (
    ConflictoEstado,
    DatosInvalidos,
    OperacionNoPermitida,
    PrecondicionNoCumplida,
)
from app.domain.horario import a_minutos, validar_hora
from app.domain.usuario import EstadoCuenta

MENSAJE_CON_HORARIOS = "Consulta de disponibilidad exitosa"
MENSAJE_SIN_HORARIOS = "No hay horarios disponibles para la fecha indicada"
MENSAJE_HORARIO_NO_DISPONIBLE = "El horario seleccionado ya no está disponible"
MENSAJE_HISTORIAL = "Consulta de historial exitosa"
MENSAJE_HISTORIAL_VACIO = "No tiene reservas en el rango de fechas indicado"
MENSAJE_RANGO_INVERTIDO = "La fecha hasta debe ser igual o posterior a la fecha desde"
NOMBRE_NO_DISPONIBLE = "No disponible"
MENSAJE_RESERVA_CERRADA = "Reserva cerrada correctamente"
MENSAJE_RESERVA_NO_EXISTE = "La reserva no existe"
MENSAJE_RESERVA_YA_CERRADA = "La reserva ya está cerrada"
MENSAJE_CIERRE_ANTICIPADO = "No se puede cerrar una reserva antes de la hora de la cita"


class EstadoReserva(str, Enum):
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"


class ResultadoCierre(str, Enum):
    """Resultado de la cita que registra la sede al cerrar la reserva (HU-40)."""

    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"


def inicio_cita(reserva: dict) -> datetime:
    return datetime.combine(reserva["fecha"], datetime.min.time()) + timedelta(
        minutes=a_minutos(reserva["hora"])
    )


def verificar_puede_cerrar(reserva: dict, ahora: datetime) -> None:
    """RN-25: solo se cierra una reserva CONFIRMED cuya cita ya empezó."""
    if reserva["estado"] != EstadoReserva.CONFIRMED:
        raise ConflictoEstado(
            MENSAJE_RESERVA_YA_CERRADA,
            {"reserva_id": reserva["reserva_id"], "estado": EstadoReserva(reserva["estado"]).value},
        )
    if ahora < inicio_cita(reserva):
        raise PrecondicionNoCumplida(
            MENSAJE_CIERRE_ANTICIPADO,
            {
                "reserva_id": reserva["reserva_id"],
                "fecha": reserva["fecha"].isoformat(),
                "hora": reserva["hora"],
            },
        )


def resena_habilitada(estado: EstadoReserva) -> bool:
    """API-I21: el usuario puede reseñar solo una reserva completada (RN-25)."""
    return estado == EstadoReserva.COMPLETED


def verificar_puede_reservar(usuario: dict) -> None:
    """RN-04: la cuenta debe estar activa para crear reservas."""
    data = {"usuario_id": usuario["usuario_id"]}
    if usuario["estado"] == EstadoCuenta.SUSPENDED:
        raise OperacionNoPermitida("Su cuenta está suspendida, no puede crear reservas", data)
    if usuario["estado"] != EstadoCuenta.ACTIVE:
        raise OperacionNoPermitida("Debe activar su cuenta antes de crear reservas", data)


def leer_fecha_consulta(valor: str) -> date:
    try:
        return leer_fecha(valor)
    except ValueError:
        raise DatosInvalidos(MENSAJE_FORMATO_FECHA, {"fecha": valor}) from None


def filtrar_horarios_libres(fecha: date, horas: list[str], reservadas: set[str], ahora: datetime) -> list[str]:
    """Quita de `horas` las reservadas y las que ya empezaron, conservando el orden."""
    inicio_dia = datetime.combine(fecha, datetime.min.time())
    return [
        hora
        for hora in horas
        if hora not in reservadas and inicio_dia + timedelta(minutes=a_minutos(hora)) >= ahora
    ]


def leer_rango_historial(desde: str | None, hasta: str | None) -> tuple[date | None, date | None]:
    """Lee los filtros opcionales `desde` y `hasta` (YYYY-MM-DD) y valida su orden."""
    fechas: dict[str, date | None] = {}
    for campo, valor in (("desde", desde), ("hasta", hasta)):
        if valor is None or not valor.strip():
            fechas[campo] = None
            continue
        try:
            fechas[campo] = leer_fecha(valor)
        except ValueError:
            raise DatosInvalidos(MENSAJE_FORMATO_FECHA, {campo: valor}) from None
    inicio, fin = fechas["desde"], fechas["hasta"]
    if inicio is not None and fin is not None and fin < inicio:
        raise DatosInvalidos(
            MENSAJE_RANGO_INVERTIDO, {"desde": inicio.isoformat(), "hasta": fin.isoformat()}
        )
    return inicio, fin


def filtrar_y_ordenar_historial(
    reservas: list[dict], desde: date | None, hasta: date | None
) -> list[dict]:
    """Deja las reservas dentro del rango y las ordena de la más reciente a la más antigua."""
    en_rango = [
        r
        for r in reservas
        if (desde is None or r["fecha"] >= desde) and (hasta is None or r["fecha"] <= hasta)
    ]
    return sorted(en_rango, key=lambda r: (r["fecha"], r["hora"], r["reserva_id"]), reverse=True)


class DisponibilidadResponse(BaseModel):
    sede_id: int
    servicio_id: int
    fecha: date
    duracion_min: int
    horarios_libres: list[str]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sede_id": 41,
                "servicio_id": 9,
                "fecha": "2026-11-20",
                "duracion_min": 60,
                "horarios_libres": ["08:00", "09:00", "11:00", "14:00", "16:00"],
            }
        }
    )


class ReservaCreate(BaseModel):
    """Datos para reservar un servicio en una sede en una fecha y hora."""

    usuario_id: int
    sede_id: int
    servicio_id: int
    fecha: date
    hora: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "usuario_id": 125,
                "sede_id": 41,
                "servicio_id": 9,
                "fecha": "2026-11-20",
                "hora": "09:00",
            }
        }
    )

    @field_validator("fecha", mode="before")
    @classmethod
    def validar_formato_fecha(cls, valor: object) -> date:
        return leer_fecha(valor)

    @field_validator("hora")
    @classmethod
    def validar_formato_hora(cls, valor: str) -> str:
        return validar_hora(valor)


class ReservaResponse(BaseModel):
    reserva_id: int
    sede: str
    servicio: str
    fecha: date
    hora: str
    estado: EstadoReserva
    correo_enviado: bool


class HistorialItem(BaseModel):
    reserva_id: int
    sede: str
    servicio: str
    fecha: date
    hora: str
    estado: EstadoReserva


class HistorialResponse(BaseModel):
    usuario_id: int
    total: int
    reservas: list[HistorialItem]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "usuario_id": 125,
                "total": 2,
                "reservas": [
                    {
                        "reserva_id": 1051,
                        "sede": "Sede Cabecera",
                        "servicio": "Limpieza facial",
                        "fecha": "2026-11-28",
                        "hora": "10:00",
                        "estado": "CONFIRMED",
                    },
                    {
                        "reserva_id": 1050,
                        "sede": "Sede Cabecera",
                        "servicio": "Masaje relajante",
                        "fecha": "2026-11-20",
                        "hora": "09:00",
                        "estado": "CONFIRMED",
                    },
                ],
            }
        }
    )


class CierreRequest(BaseModel):
    """Resultado de la cita: COMPLETED si el cliente asistió, NO_SHOW si no llegó."""

    resultado: ResultadoCierre

    model_config = ConfigDict(json_schema_extra={"example": {"resultado": "COMPLETED"}})


class CierreResponse(BaseModel):
    reserva_id: int
    estado: EstadoReserva
    resena_habilitada: bool

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"reserva_id": 1050, "estado": "COMPLETED", "resena_habilitada": True}
        }
    )
