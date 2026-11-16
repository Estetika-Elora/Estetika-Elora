"""Endpoint para generar los horarios disponibles de un servicio (HU-23).

Solo llama al servicio de disponibilidad y convierte errores en HTTP. Usa la instancia
armada en el router de sedes, la misma que se dispara al guardar un horario (HU-17).
"""

from fastapi import APIRouter, status

from app.api.respuestas import RespuestaApi, RespuestaError, a_http
from app.api.sede_router import disponibilidad
from app.domain.disponibilidad import GeneracionRequest, GeneracionResponse
from app.domain.errores import ErrorDominio

router = APIRouter(
    prefix="/api/v1/sedes/{sede_id}/servicios/{servicio_id}/horarios",
    tags=["Horarios disponibles (HU-23)"],
)


def _error(descripcion: str, mensaje: str, data: dict) -> dict:
    return {
        "model": RespuestaError,
        "description": descripcion,
        "content": {"application/json": {"example": {"message": mensaje, "data": data, "success": False}}},
    }


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=RespuestaApi[GeneracionResponse],
    responses={
        400: _error(
            "Fecha con formato inválido, desde anterior a hoy, hasta antes de desde o rango "
            "mayor a 90 días",
            "Formato de fecha no válido. Debe ser YYYY-MM-DD",
            {"desde": "16-11-2026"},
        ),
        404: _error(
            "La sede o el servicio no existe, o el servicio no se ofrece en la sede",
            "El servicio no se ofrece en la sede indicada",
            {"servicio_id": 9, "sede_id": 45},
        ),
        422: _error(
            "La sede no tiene horario de atención configurado o el servicio está inactivo",
            "La sede no tiene horario de atención configurado",
            {"sede_id": 46, "servicio_id": 9},
        ),
    },
    summary="Generar los horarios disponibles de un servicio",
    description=(
        "Divide el horario de atención de la sede (HU-17) en bloques del tamaño de la duración "
        "del servicio, para cada fecha del rango (ambas incluidas, máximo 90 días). Los días "
        "sin atención no generan bloques y un bloque que terminaría después del cierre no se "
        "crea. Se excluyen los horarios ocupados por reservas y los bloqueos de agenda (RN-13). "
        "Los bloques del rango reemplazan a los generados antes. También se ejecuta solo, para "
        "los próximos 30 días, cada vez que se guarda el horario de la sede."
    ),
)
def generar_horarios(sede_id: int, servicio_id: int, datos: GeneracionRequest):
    try:
        resultado = disponibilidad.generar(sede_id, servicio_id, datos)
    except ErrorDominio as error:
        raise a_http(error) from error
    return RespuestaApi(message="Horarios generados correctamente", data=resultado)
