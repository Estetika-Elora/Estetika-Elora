"""Errores de negocio del dominio.

Cada error lleva el texto que verá el usuario (`mensaje`) y los datos que lo causaron
(`data`). La capa API los convierte en la respuesta estándar:
{"message": ..., "data": ..., "success": false}.

El dominio no conoce HTTP: el código HTTP de cada error lo decide la capa API.
"""


class ErrorDominio(Exception):
    """Error base de las reglas de negocio."""

    def __init__(self, mensaje: str, data: dict | None = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.data = data or {}


class DatosInvalidos(ErrorDominio):
    """Los datos recibidos no cumplen una validación o regla de negocio."""


class OperacionNoPermitida(ErrorDominio):
    """La operación no está permitida en el estado actual (p. ej. empresa no aprobada)."""


class RecursoNoEncontrado(ErrorDominio):
    """El recurso solicitado no existe o no pertenece a la empresa indicada."""


class ServicioExternoNoDisponible(ErrorDominio):
    """Un servicio externo (mapas, almacenamiento) no respondió correctamente."""
