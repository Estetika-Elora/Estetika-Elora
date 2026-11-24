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


class PrecondicionNoCumplida(ErrorDominio):
    """Los datos son válidos pero falta una condición previa (p. ej. la sede sin horario)."""


class RecursoNoEncontrado(ErrorDominio):
    """El recurso solicitado no existe o no pertenece a la empresa indicada."""


class RecursoDuplicado(ErrorDominio):
    """El recurso ya existe o ya está en el estado pedido (p. ej. correo registrado, RN-01)."""


class CredencialesInvalidas(ErrorDominio):
    """El correo o la contraseña no coinciden con una cuenta."""


class CuentaBloqueada(ErrorDominio):
    """La cuenta está bloqueada temporalmente por intentos fallidos (RN-03)."""


class DemasiadasSolicitudes(ErrorDominio):
    """Se repitió una solicitud antes del tiempo de espera (p. ej. reenviar el correo)."""


class ServicioExternoNoDisponible(ErrorDominio):
    """Un servicio externo (mapas, almacenamiento, correo) no respondió correctamente."""


class ConflictoEstado(ErrorDominio):
    """El cambio de estado choca con otros datos (p. ej. desactivar una sede con reservas futuras)."""
