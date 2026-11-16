"""Endpoints del horario de atención de una sede (HU-17).

Solo llaman al servicio de sedes y convierten errores en HTTP. Usan la misma instancia de
servicio que el router de sedes (HU-16).
"""

from fastapi import APIRouter

from app.api.respuestas import RespuestaApi, RespuestaError, a_http
from app.api.sede_router import servicio
from app.domain.errores import ErrorDominio
from app.domain.horario import HorarioResponse, HorarioUpdate

router = APIRouter(prefix="/api/v1/sedes/{sede_id}/horario", tags=["Horario de sede (HU-17)"])


def _error(descripcion: str, mensaje: str, data: dict) -> dict:
    return {
        "model": RespuestaError,
        "description": descripcion,
        "content": {"application/json": {"example": {"message": mensaje, "data": data, "success": False}}},
    }


_ERROR_404 = _error("La sede no existe", "La sede no existe", {"sede_id": 99})


@router.put(
    "",
    response_model=RespuestaApi[HorarioResponse],
    responses={
        400: _error(
            "La apertura no es menor que el cierre, una hora no es HH:MM en intervalos de 15 "
            "minutos o un día está repetido. El horario anterior no cambia",
            "La hora de apertura debe ser menor que la de cierre",
            {"dia": "lunes", "apertura": "18:00", "cierre": "08:00"},
        ),
        403: _error(
            "La empresa de la sede no está aprobada (RN-07)",
            "La empresa no está aprobada para publicar en la plataforma",
            {"empresa_id": 19, "estado": "PENDING_APPROVAL"},
        ),
        404: _ERROR_404,
    },
    summary="Configurar el horario de atención de una sede",
    description=(
        "Define los días y el rango de horas en que atiende la sede (RN-13). Cada día lleva una "
        "sola franja, con horas HH:MM en intervalos de 15 minutos y la apertura menor que el "
        "cierre. El horario enviado reemplaza al anterior y los días que no se envían quedan "
        "cerrados. Al guardar se solicita regenerar los horarios disponibles (API-I19)."
    ),
)
def configurar_horario(sede_id: int, datos: HorarioUpdate):
    try:
        horario = servicio.configurar_horario(sede_id, datos)
    except ErrorDominio as error:
        raise a_http(error) from error
    return RespuestaApi(message="Horario de atención actualizado", data=horario)


@router.get(
    "",
    response_model=RespuestaApi[HorarioResponse],
    response_model_exclude_none=True,
    responses={404: _ERROR_404},
    summary="Consultar el horario de atención de una sede",
    description=(
        "Devuelve el horario configurado ordenado de lunes a domingo (API-I17). Si la sede aún "
        "no tiene horario, la lista llega vacía."
    ),
)
def obtener_horario(sede_id: int):
    try:
        horario = servicio.obtener_horario(sede_id)
    except ErrorDominio as error:
        raise a_http(error) from error
    return RespuestaApi(message="Horario de atención consultado correctamente", data=horario)
