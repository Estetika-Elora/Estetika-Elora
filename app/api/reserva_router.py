"""Endpoints de reservas (MOD-05): horarios libres (HU-36), creación de reservas (HU-37) e
historial de reservas del usuario (HU-05).

Solo llaman al servicio de reservas y convierten errores en HTTP. Reutilizan las instancias
de sedes y disponibilidad del router de sedes (HU-16, HU-23) y la de usuarios (HU-01).
El historial (/usuarios/{usuario_id}/historial) vive aquí porque usuario_router no puede
importar este módulo sin crear una importación circular.
"""

from fastapi import APIRouter, Query, status

from app.api.respuestas import RespuestaApi, RespuestaError, a_http
from app.api.sede_router import disponibilidad
from app.api.sede_router import servicio as sedes
from app.api.usuario_router import servicio as usuarios
from app.domain.disponibilidad import MENSAJE_FORMATO_FECHA
from app.domain.errores import ErrorDominio
from app.domain.reserva import (
    MENSAJE_CON_HORARIOS,
    MENSAJE_HISTORIAL,
    MENSAJE_HISTORIAL_VACIO,
    MENSAJE_HORARIO_NO_DISPONIBLE,
    MENSAJE_SIN_HORARIOS,
    DisponibilidadResponse,
    HistorialResponse,
    ReservaCreate,
    ReservaResponse,
)
from app.repository.reserva_repository import reserva_repository
from app.repository.servicio_repository import servicio_repository
from app.service.correo_service import crear_servicio_correo
from app.service.reserva_service import ReservaService
from app.service.servicio_service import ServicioService

router = APIRouter(prefix="/api/v1")
EJEMPLO_HISTORIAL = HistorialResponse.model_config["json_schema_extra"]["example"]

servicio = ReservaService(
    reserva_repository,
    disponibilidad,
    sedes,
    usuarios,
    crear_servicio_correo(),
    ServicioService(servicio_repository),
)
sedes.registrar_contador_reservas(servicio.contar_futuras)


def _error(descripcion: str, mensaje: str, data: dict) -> dict:
    return {
        "model": RespuestaError,
        "description": descripcion,
        "content": {"application/json": {"example": {"message": mensaje, "data": data, "success": False}}},
    }


@router.get(
    "/reservas/disponibilidad",
    tags=["Reservas (HU-36, HU-37)"],
    response_model=RespuestaApi[DisponibilidadResponse],
    responses={
        200: {
            "description": (
                "Horarios libres. Si no queda ninguno también responde 200, pero con "
                "success = false y horarios_libres vacío"
            ),
            "content": {
                "application/json": {
                    "examples": {
                        "con_horarios": {
                            "summary": "Hay horarios libres",
                            "value": {
                                "message": MENSAJE_CON_HORARIOS,
                                "data": {
                                    "sede_id": 41,
                                    "servicio_id": 9,
                                    "fecha": "2026-11-20",
                                    "duracion_min": 60,
                                    "horarios_libres": ["08:00", "09:00", "11:00", "14:00", "16:00"],
                                },
                                "success": True,
                            },
                        },
                        "sin_horarios": {
                            "summary": "No hay horarios libres",
                            "value": {
                                "message": MENSAJE_SIN_HORARIOS,
                                "data": {
                                    "sede_id": 41,
                                    "servicio_id": 9,
                                    "fecha": "2026-11-22",
                                    "duracion_min": 60,
                                    "horarios_libres": [],
                                },
                                "success": False,
                            },
                        },
                    }
                }
            },
        },
        400: _error(
            "La fecha no tiene el formato YYYY-MM-DD o falta un parámetro",
            "Formato de fecha no válido. Debe ser YYYY-MM-DD",
            {"fecha": "05-11-2026"},
        ),
        404: _error(
            "La sede no existe o no está activa, o el servicio no existe o no se ofrece en ella",
            "El servicio no se ofrece en la sede indicada",
            {"servicio_id": 9, "sede_id": 45},
        ),
        422: _error(
            "El servicio está inactivo",
            "El servicio no está activo",
            {"servicio_id": 11, "estado": "INACTIVE"},
        ),
    },
    summary="Consultar los horarios libres de una sede para un servicio",
    description=(
        "Devuelve las horas de inicio libres para reservar el servicio en la sede en la fecha "
        "indicada. Parte de los horarios generados por el catálogo (HU-23, API-I03), que ya "
        "respetan el horario de atención y los bloqueos de agenda (RN-13), y quita los que "
        "tienen una reserva confirmada (RN-21) y los que ya empezaron. Una fecha pasada o "
        "sin horarios generados responde la lista vacía."
    ),
)
def consultar_disponibilidad(
    sede_id: int = Query(..., description="Identificador de la sede", examples=[41]),
    servicio_id: int = Query(..., description="Identificador del servicio", examples=[9]),
    fecha: str = Query(..., description="Fecha a consultar en formato YYYY-MM-DD", examples=["2026-11-20"]),
):
    try:
        resultado = servicio.consultar_disponibilidad(sede_id, servicio_id, fecha)
    except ErrorDominio as error:
        raise a_http(error) from error
    if not resultado.horarios_libres:
        return RespuestaApi(message=MENSAJE_SIN_HORARIOS, data=resultado, success=False)
    return RespuestaApi(message=MENSAJE_CON_HORARIOS, data=resultado)


@router.post(
    "/reservas",
    tags=["Reservas (HU-36, HU-37)"],
    status_code=status.HTTP_201_CREATED,
    response_model=RespuestaApi[ReservaResponse],
    responses={
        400: _error(
            "La fecha no es YYYY-MM-DD, la hora no es HH:MM o falta un campo",
            "Formato de fecha no válido. Debe ser YYYY-MM-DD",
            {"fecha": "05-11-2026"},
        ),
        403: _error(
            "La cuenta está suspendida (RN-04) o pendiente de activación",
            "Su cuenta está suspendida, no puede crear reservas",
            {"usuario_id": 125},
        ),
        404: _error(
            "El usuario no existe, la sede no existe o no está activa, o el servicio no se "
            "ofrece en la sede indicada",
            "El servicio no se ofrece en la sede indicada",
            {"servicio_id": 9, "sede_id": 45},
        ),
        409: _error(
            "El horario no está entre los libres: ya está reservado (RN-21), ya pasó, está "
            "bloqueado o no está dentro del horario de la sede",
            MENSAJE_HORARIO_NO_DISPONIBLE,
            {"sede_id": 41, "servicio_id": 9, "fecha": "2026-11-20", "hora": "09:00"},
        ),
        422: _error(
            "El servicio está inactivo",
            "El servicio no está activo",
            {"servicio_id": 11, "estado": "INACTIVE"},
        ),
    },
    summary="Reservar un servicio en una sede con fecha y hora específicas",
    description=(
        "Crea la reserva en estado CONFIRMED si la cuenta del usuario está activa (RN-04) y el "
        "horario sigue entre los libres de HU-36 (API-I03). No puede haber dos reservas "
        "confirmadas para el mismo horario, sede y servicio (RN-21). Al confirmarse se envía "
        "un correo al usuario (API-E03); si el correo falla la reserva se conserva y "
        "correo_enviado = false. El bloqueo temporal de 10 minutos (RN-23) no aplica porque "
        "los pagos están fuera del alcance."
    ),
)
def crear_reserva(datos: ReservaCreate):
    try:
        resultado = servicio.crear(datos)
    except ErrorDominio as error:
        raise a_http(error) from error
    return RespuestaApi(message="Reserva creada correctamente", data=resultado)


@router.get(
    "/usuarios/{usuario_id}/historial",
    tags=["Usuarios (HU-05)"],
    response_model=RespuestaApi[HistorialResponse],
    responses={
        200: {
            "description": (
                "Historial del usuario, de la reserva más reciente a la más antigua. Si no hay "
                "reservas en el rango también responde 200, pero con success = false y total = 0"
            ),
            "content": {
                "application/json": {
                    "examples": {
                        "con_reservas": {
                            "summary": "El usuario tiene reservas",
                            "value": {
                                "message": MENSAJE_HISTORIAL,
                                "data": EJEMPLO_HISTORIAL,
                                "success": True,
                            },
                        },
                        "sin_reservas": {
                            "summary": "No hay reservas en el rango",
                            "value": {
                                "message": MENSAJE_HISTORIAL_VACIO,
                                "data": {"usuario_id": 125, "total": 0, "reservas": []},
                                "success": False,
                            },
                        },
                    }
                }
            },
        },
        400: _error(
            "La fecha desde o hasta no es YYYY-MM-DD, o hasta es anterior a desde",
            MENSAJE_FORMATO_FECHA,
            {"desde": "01-11-2026"},
        ),
        404: _error("El usuario no existe", "El usuario no existe", {"usuario_id": 130}),
        503: _error(
            "No responde Gestión de Reservas o la base de datos",
            "El servicio no está disponible en este momento. Intente más tarde",
            {},
        ),
    },
    summary="Consultar el historial de reservas",
    description=(
        "Devuelve en una sola lista las reservas del usuario (API-I11), en cualquier estado, "
        "de la más reciente a la más antigua. Se puede filtrar por un rango de fechas con "
        "`desde` y `hasta` (YYYY-MM-DD, ambos incluidos y opcionales)."
    ),
)
def consultar_historial(
    usuario_id: int,
    desde: str | None = Query(
        None, description="Fecha inicial del rango (YYYY-MM-DD)", examples=["2026-11-01"]
    ),
    hasta: str | None = Query(
        None, description="Fecha final del rango (YYYY-MM-DD)", examples=["2026-11-30"]
    ),
):
    try:
        resultado = servicio.consultar_historial(usuario_id, desde, hasta)
    except ErrorDominio as error:
        raise a_http(error) from error
    if not resultado.reservas:
        return RespuestaApi(message=MENSAJE_HISTORIAL_VACIO, data=resultado, success=False)
    return RespuestaApi(message=MENSAJE_HISTORIAL, data=resultado)
