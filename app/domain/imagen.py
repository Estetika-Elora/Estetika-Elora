"""Reglas de las imágenes que se suben a la plataforma (HU-31)."""

from dataclasses import dataclass

from app.domain.errores import DatosInvalidos

TIPOS_PERMITIDOS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
TAMANO_MAXIMO_BYTES = 5 * 1024 * 1024  # 5 MB
MAXIMO_IMAGENES = 5


@dataclass(frozen=True)
class ArchivoImagen:
    """Imagen recibida en la petición, ya leída en memoria.

    La capa API la construye a partir del archivo subido para que el resto de capas
    no dependa de FastAPI.
    """

    nombre: str
    tipo_contenido: str
    contenido: bytes

    @property
    def extension(self) -> str:
        return TIPOS_PERMITIDOS[self.tipo_contenido]


def _firma_coincide(tipo_contenido: str, contenido: bytes) -> bool:
    """Comprueba los primeros bytes del archivo: el tipo declarado por el cliente no basta."""
    if tipo_contenido == "image/jpeg":
        return contenido.startswith(b"\xff\xd8\xff")
    if tipo_contenido == "image/png":
        return contenido.startswith(b"\x89PNG\r\n\x1a\n")
    if tipo_contenido == "image/webp":
        return contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP"
    return False


def validar_imagenes(imagenes: list[ArchivoImagen], obligatorio: bool) -> None:
    """Valida cantidad, formato y tamaño de las imágenes antes de subir cualquiera."""
    if obligatorio and not imagenes:
        raise DatosInvalidos("Debe enviar al menos una imagen del producto", {"imagenes": 0})
    if len(imagenes) > MAXIMO_IMAGENES:
        raise DatosInvalidos(
            f"Solo se permiten {MAXIMO_IMAGENES} imágenes por producto",
            {"imagenes": len(imagenes)},
        )
    for imagen in imagenes:
        if not imagen.contenido:
            raise DatosInvalidos("La imagen está vacía", {"imagen": imagen.nombre})
        if imagen.tipo_contenido not in TIPOS_PERMITIDOS or not _firma_coincide(
            imagen.tipo_contenido, imagen.contenido
        ):
            raise DatosInvalidos(
                "Formato de imagen no permitido. Use JPG, PNG o WEBP",
                {"imagen": imagen.nombre, "tipo": imagen.tipo_contenido},
            )
        if len(imagen.contenido) > TAMANO_MAXIMO_BYTES:
            raise DatosInvalidos(
                "La imagen supera el tamaño máximo de 5 MB", {"imagen": imagen.nombre}
            )
