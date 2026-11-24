"""Endpoints de sedes (HU-16) y de su estado (HU-20). Solo llaman al servicio y convierten errores en HTTP.

Aquí también se arman los servicios de sedes y de disponibilidad (HU-23) y se conectan
entre sí, para que guardar el horario de una sede (HU-17) regenere sus horarios.
"""

import os

from fastapi import APIRouter, status

from app.api.respuestas import RESPUESTAS_ERROR, RespuestaApi, RespuestaError, a_http
from app.domain.errores import ErrorDominio
from app.domain.sede import (
    SedeCreate,
    SedeEstadoResponse,
    SedeEstadoUpdate,
    SedeResponse,
    SedeUpdate,
)
from app.repository.bloque_horario_repository import bloque_horario_repository
from app.repository.empresa_repository import empresa_repository
from app.repository.sede_repository import sede_repository
from app.repository.servicio_repository import servicio_repository
from app.service.disponibilidad_service import DisponibilidadService
from app.service.empresa_service import EmpresaService
from app.service.mapas_service import MapasService
from app.service.sede_service import SedeService
from app.service.servicio_service import ServicioService

router = APIRouter(prefix="/api/v1/empresas/{empresa_id}/sedes", tags=["Sedes (HU-16)"])
router_sede = APIRouter(prefix="/api/v1/sedes", tags=["Sedes (HU-20)"])

servicio = SedeService(
    sede_repository,
    EmpresaService(empresa_repository),
    MapasService(os.getenv("NOMINATIM_USER_AGENT", "EstetikaElora/0.1 (proyecto academico)")),
)
disponibilidad = DisponibilidadService(
    servicio, ServicioService(servicio_repository), bloque_horario_repository
)
servicio.registrar_regenerador(disponibilidad.regenerar_sede)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=RespuestaApi[SedeResponse],
    responses=RESPUESTAS_ERROR,
    summary="Registrar una sede con dirección validada en el mapa",
    description=(
        "Crea una sede para una empresa aprobada (RN-07). La dirección se valida con "
        "Nominatim de OpenStreetMap (API-E04) y se guardan su latitud y longitud."
    ),
)
def crear_sede(empresa_id: int, datos: SedeCreate):
    try:
        sede = servicio.crear(empresa_id, datos)
    except ErrorDominio as error:
        raise a_http(error) from error
    return RespuestaApi(message="Sede registrada correctamente", data=sede)


@router.get(
    "",
    response_model=RespuestaApi[list[SedeResponse]],
    responses={404: RESPUESTAS_ERROR[404]},
    summary="Listar las sedes de una empresa",
)
def listar_sedes(empresa_id: int):
    try:
        sedes = servicio.listar(empresa_id)
    except ErrorDominio as error:
        raise a_http(error) from error
    return RespuestaApi(message="Sedes consultadas correctamente", data=sedes)


@router.get(
    "/{sede_id}",
    response_model=RespuestaApi[SedeResponse],
    responses={404: RESPUESTAS_ERROR[404]},
    summary="Consultar una sede",
)
def obtener_sede(empresa_id: int, sede_id: int):
    try:
        sede = servicio.obtener(empresa_id, sede_id)
    except ErrorDominio as error:
        raise a_http(error) from error
    return RespuestaApi(message="Sede consultada correctamente", data=sede)


@router.put(
    "/{sede_id}",
    response_model=RespuestaApi[SedeResponse],
    responses=RESPUESTAS_ERROR,
    summary="Editar una sede",
    description=(
        "Edición parcial: solo se cambian los campos enviados. Si cambia la dirección o la "
        "ciudad, se vuelve a validar en el mapa."
    ),
)
def actualizar_sede(empresa_id: int, sede_id: int, datos: SedeUpdate):
    try:
        sede = servicio.actualizar(empresa_id, sede_id, datos)
    except ErrorDominio as error:
        raise a_http(error) from error
    return RespuestaApi(message="Sede actualizada correctamente", data=sede)


@router.delete(
    "/{sede_id}",
    response_model=RespuestaApi[SedeResponse],
    responses={403: RESPUESTAS_ERROR[403], 404: RESPUESTAS_ERROR[404]},
    summary="Eliminar una sede",
)
def eliminar_sede(empresa_id: int, sede_id: int):
    try:
        sede = servicio.eliminar(empresa_id, sede_id)
    except ErrorDominio as error:
        raise a_http(error) from error
    return RespuestaApi(message="Sede eliminada correctamente", data=sede)


@router_sede.patch(
    "/{sede_id}/estado",
    response_model=RespuestaApi[SedeEstadoResponse],
    responses={
        **RESPUESTAS_ERROR,
        409: {
            "model": RespuestaError,
            "description": "La sede tiene reservas futuras confirmadas (RN-10) o ya está en ese estado",
            "content": {
                "application/json": {
                    "example": {
                        "message": "No se puede desactivar la sede porque tiene reservas futuras confirmadas",
                        "data": {"sede_id": 41, "reservas_futuras": 3},
                        "success": False,
                    }
                }
            },
        },
    },
    summary="Activar o desactivar una sede",
    description=(
        "INACTIVE retira la sede: no se puede consultar su disponibilidad ni reservar en ella. "
        "No se permite desactivarla si tiene reservas futuras confirmadas (RN-10, API-I18). "
        "ACTIVE la vuelve a publicar y regenera sus horarios disponibles (API-I19). "
        "Solo empresas aprobadas (RN-07)."
    ),
)
def cambiar_estado_sede(sede_id: int, datos: SedeEstadoUpdate):
    try:
        resultado = servicio.cambiar_estado(sede_id, datos)
    except ErrorDominio as error:
        raise a_http(error) from error
    return RespuestaApi(message="Estado de la sede actualizado", data=resultado)
