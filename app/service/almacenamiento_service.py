"""Almacenamiento de imágenes (API-E05).

Dos implementaciones con los mismos métodos (`guardar` y `eliminar`):
- AlmacenamientoCloudinary: sube a la nube (plan gratuito). Se usa si hay credenciales.
- AlmacenamientoLocal: guarda en la carpeta uploads/ del proyecto. Para desarrollar sin cuenta.

`crear_almacenamiento()` elige la implementación según las variables de entorno.
La subida a Cloudinary se hace con httpx y una firma SHA-1, sin instalar su librería.
"""

import hashlib
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.domain.errores import ServicioExternoNoDisponible
from app.domain.imagen import ArchivoImagen

_MENSAJE_FALLO = "No fue posible almacenar las imágenes en este momento"


@dataclass(frozen=True)
class ImagenGuardada:
    url: str  # URL pública que se entrega al cliente
    identificador: str  # Lo necesario para borrarla después


class AlmacenamientoLocal:
    def __init__(self, carpeta: Path, url_base: str) -> None:
        self.carpeta = carpeta
        self._url_base = url_base.rstrip("/")
        self.carpeta.mkdir(parents=True, exist_ok=True)

    def guardar(self, archivo: ArchivoImagen, subcarpeta: str) -> ImagenGuardada:
        nombre = f"{uuid.uuid4().hex}.{archivo.extension}"
        identificador = f"{subcarpeta}/{nombre}"
        try:
            destino = self.carpeta / subcarpeta
            destino.mkdir(parents=True, exist_ok=True)
            (destino / nombre).write_bytes(archivo.contenido)
        except OSError as error:
            raise ServicioExternoNoDisponible(_MENSAJE_FALLO, {}) from error
        return ImagenGuardada(url=f"{self._url_base}/uploads/{identificador}", identificador=identificador)

    def eliminar(self, identificador: str) -> None:
        try:
            (self.carpeta / identificador).unlink(missing_ok=True)
        except OSError as error:
            raise ServicioExternoNoDisponible("No fue posible eliminar la imagen", {}) from error


class AlmacenamientoCloudinary:
    _URL_API = "https://api.cloudinary.com/v1_1/{nube}/image/{accion}"

    def __init__(
        self, cloud_name: str, api_key: str, api_secret: str, carpeta_raiz: str, timeout: float = 30.0
    ) -> None:
        self._cloud_name = cloud_name
        self._api_key = api_key
        self._api_secret = api_secret
        self._carpeta_raiz = carpeta_raiz.strip("/")
        self._timeout = timeout

    def _firmar(self, parametros: dict[str, str]) -> str:
        """Firma de Cloudinary: parámetros ordenados "a=1&b=2" + secreto, en SHA-1."""
        cadena = "&".join(f"{clave}={valor}" for clave, valor in sorted(parametros.items()))
        return hashlib.sha1((cadena + self._api_secret).encode("utf-8")).hexdigest()

    def _peticion(self, accion: str, parametros: dict[str, str], archivos: dict | None = None) -> dict:
        datos = {**parametros, "api_key": self._api_key, "signature": self._firmar(parametros)}
        try:
            respuesta = httpx.post(
                self._URL_API.format(nube=self._cloud_name, accion=accion),
                data=datos,
                files=archivos,
                timeout=self._timeout,
            )
        except httpx.HTTPError as error:
            raise ServicioExternoNoDisponible(_MENSAJE_FALLO, {}) from error
        if respuesta.status_code != 200:
            raise ServicioExternoNoDisponible(_MENSAJE_FALLO, {"codigo_servicio": respuesta.status_code})
        return respuesta.json()

    def guardar(self, archivo: ArchivoImagen, subcarpeta: str) -> ImagenGuardada:
        parametros = {
            "folder": f"{self._carpeta_raiz}/{subcarpeta}",
            "timestamp": str(int(time.time())),
        }
        nombre = archivo.nombre or f"imagen.{archivo.extension}"
        resultado = self._peticion(
            "upload", parametros, {"file": (nombre, archivo.contenido, archivo.tipo_contenido)}
        )
        return ImagenGuardada(url=resultado["secure_url"], identificador=resultado["public_id"])

    def eliminar(self, identificador: str) -> None:
        parametros = {"public_id": identificador, "timestamp": str(int(time.time()))}
        resultado = self._peticion("destroy", parametros)
        if resultado.get("result") not in ("ok", "not found"):
            raise ServicioExternoNoDisponible("No fue posible eliminar la imagen", {})


def _credenciales_cloudinary() -> tuple[str, str, str] | None:
    nube = os.getenv("CLOUDINARY_CLOUD_NAME", "").strip()
    clave = os.getenv("CLOUDINARY_API_KEY", "").strip()
    secreto = os.getenv("CLOUDINARY_API_SECRET", "").strip()
    if nube and clave and secreto:
        return nube, clave, secreto
    # Alternativa: CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name
    url = os.getenv("CLOUDINARY_URL", "").strip()
    if url:
        partes = urlparse(url)
        if partes.scheme == "cloudinary" and partes.hostname and partes.username and partes.password:
            return partes.hostname, partes.username, partes.password
    return None


def crear_almacenamiento() -> AlmacenamientoCloudinary | AlmacenamientoLocal:
    credenciales = _credenciales_cloudinary()
    if credenciales:
        nube, clave, secreto = credenciales
        return AlmacenamientoCloudinary(
            nube, clave, secreto, os.getenv("CLOUDINARY_FOLDER", "estetika-elora")
        )
    return AlmacenamientoLocal(
        Path(os.getenv("UPLOADS_DIR", "uploads")),
        os.getenv("PUBLIC_BASE_URL", "http://localhost:8000"),
    )
