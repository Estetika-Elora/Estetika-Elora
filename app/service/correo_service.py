"""Envío de correos (API-E03).

Dos implementaciones con el mismo método (`enviar`):
- CorreoBrevo: envía con la API REST transaccional de Brevo (plan gratuito, 300 correos al
  día). Se usa si hay BREVO_API_KEY y CORREO_REMITENTE.
- CorreoConsola: imprime el correo en la terminal del servidor. Para desarrollar sin cuenta.

`crear_servicio_correo()` elige la implementación según las variables de entorno.
La petición a Brevo se hace con httpx, sin instalar su librería.
"""

import os
from dataclasses import dataclass

import httpx

from app.domain.errores import ServicioExternoNoDisponible

_MENSAJE_FALLO = "No fue posible enviar el correo en este momento. Intente más tarde"


@dataclass(frozen=True)
class Correo:
    destinatario: str
    nombre_destinatario: str
    asunto: str
    html: str
    texto: str


class CorreoConsola:
    def enviar(self, correo: Correo) -> None:
        separador = "=" * 70
        print(
            f"\n{separador}\n[CORREO - modo consola, no se envió]\n"
            f"Para: {correo.nombre_destinatario} <{correo.destinatario}>\n"
            f"Asunto: {correo.asunto}\n\n{correo.texto}\n{separador}\n",
            flush=True,
        )


class CorreoBrevo:
    _URL_API = "https://api.brevo.com/v3/smtp/email"

    def __init__(self, api_key: str, remitente: str, nombre_remitente: str, timeout: float = 15.0) -> None:
        self._api_key = api_key
        self._remitente = remitente
        self._nombre_remitente = nombre_remitente
        self._timeout = timeout

    def enviar(self, correo: Correo) -> None:
        cuerpo = {
            "sender": {"name": self._nombre_remitente, "email": self._remitente},
            "to": [{"email": correo.destinatario, "name": correo.nombre_destinatario}],
            "subject": correo.asunto,
            "htmlContent": correo.html,
            "textContent": correo.texto,
        }
        try:
            respuesta = httpx.post(
                self._URL_API,
                json=cuerpo,
                headers={"api-key": self._api_key, "accept": "application/json"},
                timeout=self._timeout,
            )
        except httpx.HTTPError as error:
            raise ServicioExternoNoDisponible(_MENSAJE_FALLO, {}) from error
        if respuesta.status_code not in (200, 201, 202):
            raise ServicioExternoNoDisponible(_MENSAJE_FALLO, {"codigo_servicio": respuesta.status_code})


def crear_servicio_correo() -> CorreoBrevo | CorreoConsola:
    api_key = os.getenv("BREVO_API_KEY", "").strip()
    remitente = os.getenv("CORREO_REMITENTE", "").strip()
    nombre = os.getenv("CORREO_REMITENTE_NOMBRE", "").strip() or "Estetika Elora"
    if api_key and remitente:
        return CorreoBrevo(api_key, remitente, nombre)
    return CorreoConsola()
