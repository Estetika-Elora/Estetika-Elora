"""Endpoints de empresas (HU-11, HU-14 y HU-19). La lógica de negocio vive en EmpresaService.

La edición de la empresa (HU-14) recibe multipart/form-data porque puede incluir el logo.
"""

from fastapi import APIRouter, File, Form, UploadFile, status
from pydantic import ValidationError

from app.api.respuestas import (
    RESPUESTAS_ERROR,
    RespuestaApi,
    RespuestaError,
    a_http,
    error_validacion,
)
from app.domain.empresa import (
    EmpresaCreate,
    EmpresaPerfilResponse,
    EmpresaResponse,
    EmpresaUpdate,
    PoliticaCancelacionResponse,
    PoliticaCancelacionUpdate,
)
from app.domain.errores import ErrorDominio
from app.domain.imagen import TAMANO_MAXIMO_BYTES, ArchivoImagen
from app.repository.empresa_repository import empresa_repository
from app.service.almacenamiento_service import crear_almacenamiento
from app.service.correo_service import crear_servicio_correo
from app.service.empresa_service import EmpresaService

router = APIRouter(prefix="/api/v1")

servicio = EmpresaService(
    repositorio=empresa_repository,
    correo=crear_servicio_correo(),
    almacenamiento=crear_almacenamiento(),
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


RESPUESTAS_EDITAR_EMPRESA = {
    400: {
        "model": RespuestaError,
        "description": "Datos inválidos o intento de cambiar el NIT o la razón social",
    },
    404: RESPUESTAS_ERROR[404],
    503: {"model": RespuestaError, "description": "El almacenamiento de imágenes no está disponible"},
}


def _leer_logo(archivo: UploadFile | None) -> ArchivoImagen | None:
    """Pasa el logo subido a un objeto del dominio; lee como máximo 5 MB + 1 byte."""
    if archivo is None or not archivo.filename:
        return None
    return ArchivoImagen(
        nombre=archivo.filename,
        tipo_contenido=archivo.content_type or "",
        contenido=archivo.file.read(TAMANO_MAXIMO_BYTES + 1),
    )


@router.put(
    "/empresas/{empresa_id}",
    tags=["Empresas (HU-14)"],
    response_model=RespuestaApi[EmpresaPerfilResponse],
    responses=RESPUESTAS_EDITAR_EMPRESA,
    summary="Editar la información de la empresa",
    description=(
        "Edición parcial del perfil comercial: solo se cambian los campos enviados "
        "(descripción, teléfono, correo de contacto y logo). El NIT y la razón social no se "
        "pueden modificar (RN-06): si se envían con un valor distinto se responde 400. "
        "El logo (JPG, PNG o WEBP, máximo 5 MB) se guarda en el almacenamiento (API-E05) y "
        "reemplaza al anterior. La validación de que el usuario administre la empresa (403) "
        "queda pendiente hasta que las rutas validen el token."
    ),
)
def editar_empresa(
    empresa_id: int,
    descripcion: str | None = Form(
        None, examples=["Centro de estética facial y corporal con 3 sedes en Bucaramanga"]
    ),
    telefono: str | None = Form(None, description="10 dígitos", examples=["6076345120"]),
    correo_contacto: str | None = Form(None, examples=["contacto@bellapiel.com"]),
    nit: str | None = Form(None, description="No modificable: solo se compara con el actual"),
    razon_social: str | None = Form(
        None, description="No modificable: solo se compara con la actual"
    ),
    logo: UploadFile | None = File(None, description="Opcional: reemplaza el logo actual"),
):
    try:
        datos = EmpresaUpdate(
            nit=nit,
            razon_social=razon_social,
            descripcion=descripcion,
            telefono=telefono,
            correo_contacto=correo_contacto,
        )
    except ValidationError as error:
        raise error_validacion(error.errors()) from error
    try:
        empresa = servicio.actualizar_perfil(empresa_id, datos, _leer_logo(logo))
    except ErrorDominio as error:
        raise a_http(error) from error
    return RespuestaApi(message="Empresa actualizada correctamente", data=empresa)


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
