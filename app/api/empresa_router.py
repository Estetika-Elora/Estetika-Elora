"""Endpoints de empresas (HU-11 y HU-19). La lógica de negocio vive en EmpresaService."""

from fastapi import APIRouter, status

from app.api.respuestas import RESPUESTAS_ERROR, RespuestaApi, RespuestaError, a_http
from app.domain.empresa import (
    EmpresaCreate,
    EmpresaResponse,
    PoliticaCancelacionResponse,
    PoliticaCancelacionUpdate,
)
from app.domain.errores import ErrorDominio
from app.repository.empresa_repository import empresa_repository
from app.service.correo_service import crear_servicio_correo
from app.service.empresa_service import EmpresaService

router = APIRouter(prefix="/api/v1")

servicio = EmpresaService(
    repositorio=empresa_repository,
    correo=crear_servicio_correo(),
)

RESPUESTAS_EMPRESA = {
    **RESPUESTAS_ERROR,
    409: {"model": RespuestaError, "description": "El NIT ya se encuentra registrado"},
}


@router.post(
    "/empresas",
    tags=["Empresas (HU-11)"],
    status_code=status.HTTP_201_CREATED,
    response_model=RespuestaApi[EmpresaResponse],
    responses=RESPUESTAS_EMPRESA,
    summary="Registrar una empresa en Estetika Elora",
    description=(
        "Registra una empresa con NIT único. La solicitud queda en estado "
        "PENDING_APPROVAL y se envía un correo de confirmación al representante (API-E03)."
    ),
)
def crear_empresa(datos: EmpresaCreate):
    try:
        empresa = servicio.registrar(datos)
    except ErrorDominio as error:
        raise a_http(error) from error

    return RespuestaApi(
        message="Empresa registrada, pendiente de aprobación",
        data=empresa,
    )


@router.get(
    "/empresas",
    tags=["Empresas (HU-11)"],
    response_model=RespuestaApi[list[EmpresaResponse]],
    responses=RESPUESTAS_ERROR,
    summary="Obtener todas las empresas",
)
def listar_empresas():
    empresas = servicio.listar()

    return RespuestaApi(
        message="Empresas consultadas correctamente",
        data=empresas,
    )


@router.get(
    "/empresas/{empresa_id}",
    tags=["Empresas (HU-11)"],
    response_model=RespuestaApi[EmpresaResponse],
    responses=RESPUESTAS_ERROR,
    summary="Obtener empresa por ID",
)
def obtener_empresa(empresa_id: int):
    """Obtiene una empresa mediante su identificador."""

    try:
        empresa = servicio.obtener(empresa_id)
    except ErrorDominio as error:
        raise a_http(error) from error

    return RespuestaApi(
        message="Empresa consultada correctamente",
        data=empresa,
    )


@router.put(
    "/empresas/{empresa_id}/politica-cancelacion",
    tags=["Empresas (HU-11)"],
    response_model=RespuestaApi[PoliticaCancelacionResponse],
    responses=RESPUESTAS_ERROR,
    summary="Configurar la política de cancelación de la empresa",
    description=(
        "Define cuántas horas antes de la cita se puede cancelar o reprogramar una reserva "
        "(RN-24). El valor debe estar entre 1 y 72 horas y aplica a todas las sedes de la "
        "empresa. Solo empresas aprobadas (RN-07). Si no se configura, se aplican 24 horas."
    ),
)
def configurar_politica_cancelacion(empresa_id: int, datos: PoliticaCancelacionUpdate):
    try:
        politica = servicio.configurar_politica_cancelacion(empresa_id, datos)
    except ErrorDominio as error:
        raise a_http(error) from error

    return RespuestaApi(message="Política de cancelación guardada", data=politica)
