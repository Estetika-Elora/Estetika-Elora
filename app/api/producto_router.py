"""Endpoints de productos (HU-31). Solo llaman al servicio y convierten errores en HTTP.

POST y PUT reciben multipart/form-data porque incluyen imágenes.
"""

from fastapi import APIRouter, File, Form, UploadFile, status
from pydantic import ValidationError

from app.api.respuestas import RESPUESTAS_ERROR, RespuestaApi, a_http, error_validacion
from app.domain.errores import ErrorDominio
from app.domain.imagen import TAMANO_MAXIMO_BYTES, ArchivoImagen
from app.domain.producto import ProductoCreate, ProductoResponse, ProductoUpdate
from app.repository.empresa_repository import empresa_repository
from app.repository.producto_repository import producto_repository
from app.service.almacenamiento_service import crear_almacenamiento
from app.service.empresa_service import EmpresaService
from app.service.producto_service import ProductoService

router = APIRouter(prefix="/api/v1/empresas/{empresa_id}/productos", tags=["Productos (HU-31)"])

almacenamiento = crear_almacenamiento()
servicio = ProductoService(producto_repository, EmpresaService(empresa_repository), almacenamiento)


def _leer_imagenes(archivos: list[UploadFile] | None) -> list[ArchivoImagen]:
    """Pasa los archivos subidos a objetos del dominio, sin dependencia de FastAPI.

    Lee como máximo 5 MB + 1 byte por archivo: basta para saber si supera el límite.
    """
    return [
        ArchivoImagen(
            nombre=archivo.filename or "",
            tipo_contenido=archivo.content_type or "",
            contenido=archivo.file.read(TAMANO_MAXIMO_BYTES + 1),
        )
        for archivo in archivos or []
        if archivo.filename  # Swagger puede enviar un campo de archivo vacío
    ]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=RespuestaApi[ProductoResponse],
    responses=RESPUESTAS_ERROR,
    summary="Publicar un producto con precio, stock e imágenes",
    description=(
        "Crea un producto para una empresa aprobada (RN-07). Precio mayor que cero y stock no "
        "negativo (RN-16). Entre 1 y 5 imágenes JPG, PNG o WEBP de máximo 5 MB, que se "
        "guardan en Cloudinary (API-E05)."
    ),
)
def crear_producto(
    empresa_id: int,
    nombre: str = Form(..., examples=["Sérum de vitamina C 30 ml"]),
    categoria: str = Form(..., examples=["Cuidado facial"]),
    descripcion: str = Form(..., examples=["Sérum antioxidante para todo tipo de piel"]),
    precio: int = Form(..., description="Pesos colombianos, sin decimales", examples=[68000]),
    stock: int = Form(..., examples=[25]),
    imagenes: list[UploadFile] = File(..., description="Entre 1 y 5 imágenes"),
):
    try:
        datos = ProductoCreate(
            nombre=nombre, categoria=categoria, descripcion=descripcion, precio=precio, stock=stock
        )
    except ValidationError as error:
        raise error_validacion(error.errors()) from error
    try:
        producto = servicio.crear(empresa_id, datos, _leer_imagenes(imagenes))
    except ErrorDominio as error:
        raise a_http(error) from error
    return RespuestaApi(message="Producto publicado correctamente", data=producto)


@router.get(
    "",
    response_model=RespuestaApi[list[ProductoResponse]],
    responses={404: RESPUESTAS_ERROR[404]},
    summary="Listar los productos de una empresa",
)
def listar_productos(empresa_id: int):
    try:
        productos = servicio.listar(empresa_id)
    except ErrorDominio as error:
        raise a_http(error) from error
    return RespuestaApi(message="Productos consultados correctamente", data=productos)


@router.get(
    "/{producto_id}",
    response_model=RespuestaApi[ProductoResponse],
    responses={404: RESPUESTAS_ERROR[404]},
    summary="Consultar un producto",
)
def obtener_producto(empresa_id: int, producto_id: int):
    try:
        producto = servicio.obtener(empresa_id, producto_id)
    except ErrorDominio as error:
        raise a_http(error) from error
    return RespuestaApi(message="Producto consultado correctamente", data=producto)


@router.put(
    "/{producto_id}",
    response_model=RespuestaApi[ProductoResponse],
    responses=RESPUESTAS_ERROR,
    summary="Editar un producto",
    description=(
        "Edición parcial: solo se cambian los campos enviados. Si se envían imágenes, "
        "reemplazan a las anteriores, que se borran del almacenamiento."
    ),
)
def actualizar_producto(
    empresa_id: int,
    producto_id: int,
    nombre: str | None = Form(None),
    categoria: str | None = Form(None),
    descripcion: str | None = Form(None),
    precio: int | None = Form(None, description="Pesos colombianos, sin decimales"),
    stock: int | None = Form(None),
    # Lista vacía por defecto: con `list[UploadFile] | None` FastAPI 0.111 solo toma un archivo.
    imagenes: list[UploadFile] = File([], description="Opcional: reemplaza las imágenes"),
):
    try:
        datos = ProductoUpdate(
            nombre=nombre, categoria=categoria, descripcion=descripcion, precio=precio, stock=stock
        )
    except ValidationError as error:
        raise error_validacion(error.errors()) from error
    try:
        producto = servicio.actualizar(empresa_id, producto_id, datos, _leer_imagenes(imagenes))
    except ErrorDominio as error:
        raise a_http(error) from error
    return RespuestaApi(message="Producto actualizado correctamente", data=producto)


@router.delete(
    "/{producto_id}",
    response_model=RespuestaApi[ProductoResponse],
    responses={403: RESPUESTAS_ERROR[403], 404: RESPUESTAS_ERROR[404]},
    summary="Eliminar un producto",
    description="Elimina el producto y borra sus imágenes del almacenamiento.",
)
def eliminar_producto(empresa_id: int, producto_id: int):
    try:
        producto = servicio.eliminar(empresa_id, producto_id)
    except ErrorDominio as error:
        raise a_http(error) from error
    return RespuestaApi(message="Producto eliminado correctamente", data=producto)
