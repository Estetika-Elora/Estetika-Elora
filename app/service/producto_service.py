"""Servicio de productos (HU-31 · PRO-31): CRUD de productos con imágenes en la nube."""

import logging

from app.domain.errores import DatosInvalidos, ErrorDominio, RecursoNoEncontrado
from app.domain.estados import EstadoRegistro
from app.domain.imagen import ArchivoImagen, validar_imagenes
from app.domain.producto import ProductoCreate, ProductoResponse, ProductoUpdate
from app.repository.producto_repository import ProductoRepository
from app.service.almacenamiento_service import (
    AlmacenamientoCloudinary,
    AlmacenamientoLocal,
    ImagenGuardada,
)
from app.service.empresa_service import EmpresaService

logger = logging.getLogger(__name__)

SUBCARPETA_PRODUCTOS = "productos"


class ProductoService:
    def __init__(
        self,
        repositorio: ProductoRepository,
        empresa_service: EmpresaService,
        almacenamiento: AlmacenamientoCloudinary | AlmacenamientoLocal,
    ) -> None:
        self._repositorio = repositorio
        self._empresas = empresa_service
        self._almacenamiento = almacenamiento

    def crear(
        self, empresa_id: int, datos: ProductoCreate, imagenes: list[ArchivoImagen]
    ) -> ProductoResponse:
        self._empresas.verificar_aprobada(empresa_id)  # RN-07
        validar_imagenes(imagenes, obligatorio=True)  # Antes de subir cualquier imagen
        guardadas = self._subir(imagenes)
        producto = self._repositorio.crear(
            {
                "empresa_id": empresa_id,
                **datos.model_dump(),
                "imagenes": [vars(g) for g in guardadas],
                "estado": EstadoRegistro.ACTIVE,
            }
        )
        return self._a_respuesta(producto)

    def listar(self, empresa_id: int) -> list[ProductoResponse]:
        self._empresas.obtener(empresa_id)
        return [self._a_respuesta(p) for p in self._repositorio.listar_por_empresa(empresa_id)]

    def obtener(self, empresa_id: int, producto_id: int) -> ProductoResponse:
        self._empresas.obtener(empresa_id)
        return self._a_respuesta(self._buscar_de_empresa(empresa_id, producto_id))

    def actualizar(
        self,
        empresa_id: int,
        producto_id: int,
        datos: ProductoUpdate,
        imagenes: list[ArchivoImagen],
    ) -> ProductoResponse:
        """Edición parcial. Si llegan imágenes, reemplazan a las anteriores."""
        self._empresas.verificar_aprobada(empresa_id)  # RN-07
        producto = self._buscar_de_empresa(empresa_id, producto_id)
        cambios = datos.model_dump(exclude_none=True)
        if not cambios and not imagenes:
            raise DatosInvalidos("Debe enviar al menos un campo o una imagen para actualizar", {})

        imagenes_anteriores: list[dict] = []
        if imagenes:
            validar_imagenes(imagenes, obligatorio=True)
            cambios["imagenes"] = [vars(g) for g in self._subir(imagenes)]
            imagenes_anteriores = producto["imagenes"]

        actualizado = self._repositorio.actualizar(producto_id, cambios)
        self._borrar_sin_fallar(imagenes_anteriores)
        return self._a_respuesta(actualizado)

    def eliminar(self, empresa_id: int, producto_id: int) -> ProductoResponse:
        self._empresas.verificar_aprobada(empresa_id)  # RN-07
        self._buscar_de_empresa(empresa_id, producto_id)
        eliminado = self._repositorio.eliminar(producto_id)
        self._borrar_sin_fallar(eliminado["imagenes"])
        return self._a_respuesta(eliminado)

    def _buscar_de_empresa(self, empresa_id: int, producto_id: int) -> dict:
        """Un producto de otra empresa se trata como inexistente."""
        producto = self._repositorio.obtener_por_id(producto_id)
        if producto is None or producto["empresa_id"] != empresa_id:
            raise RecursoNoEncontrado("El producto no existe", {"producto_id": producto_id})
        return producto

    def _subir(self, imagenes: list[ArchivoImagen]) -> list[ImagenGuardada]:
        """Sube todas las imágenes; si una falla, borra las que ya se subieron."""
        guardadas: list[ImagenGuardada] = []
        try:
            for imagen in imagenes:
                guardadas.append(self._almacenamiento.guardar(imagen, SUBCARPETA_PRODUCTOS))
        except ErrorDominio:
            self._borrar_sin_fallar([vars(g) for g in guardadas])
            raise
        return guardadas

    def _borrar_sin_fallar(self, imagenes: list[dict]) -> None:
        """Borra imágenes que ya no se usan. Si falla, solo se registra: no se revierte la operación."""
        for imagen in imagenes:
            try:
                self._almacenamiento.eliminar(imagen["identificador"])
            except ErrorDominio:
                logger.warning("No se pudo borrar la imagen %s", imagen["identificador"])

    @staticmethod
    def _a_respuesta(producto: dict) -> ProductoResponse:
        return ProductoResponse.model_validate(
            {**producto, "imagenes": [imagen["url"] for imagen in producto["imagenes"]]}
        )
