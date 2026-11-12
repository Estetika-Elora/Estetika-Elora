"""Endpoints de sedes (HU-16). Solo llaman al servicio y convierten errores en HTTP."""

import os

from fastapi import APIRouter, status

from app.api.respuestas import RESPUESTAS_ERROR, RespuestaApi, a_http
from app.domain.errores import ErrorDominio
from app.domain.sede import SedeCreate, SedeResponse, SedeUpdate
from app.repository.empresa_repository import empresa_repository
from app.repository.sede_repository import sede_repository
from app.service.empresa_service import EmpresaService
from app.service.mapas_service import MapasService
from app.service.sede_service import SedeService

router = APIRouter(prefix="/api/v1/empresas/{empresa_id}/sedes", tags=["Sedes (HU-16)"])

servicio = SedeService(
    sede_repository,
    EmpresaService(empresa_repository),
    MapasService(os.getenv("NOMINATIM_USER_AGENT", "EstetikaElora/0.1 (proyecto academico)")),
)


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
