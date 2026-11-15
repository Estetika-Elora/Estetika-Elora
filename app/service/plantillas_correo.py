"""Plantillas de los correos que envía la plataforma.

El HTML usa tablas y estilos en línea porque los clientes de correo (Gmail, Outlook) no
soportan hojas de estilo externas. Cada plantilla trae también una versión en texto plano.
Los datos del usuario se escapan para que no se pueda inyectar HTML en el correo.
"""

from html import escape

from app.service.correo_service import Correo

COLOR_MARCA = "#B4567E"
COLOR_MARCA_OSCURO = "#8E3F63"
COLOR_FONDO = "#F7EEF2"


def correo_activacion(destinatario: str, nombre: str, enlace: str, vigencia_horas: int) -> Correo:
    primer_nombre = nombre.split()[0]
    nombre_html = escape(primer_nombre)
    enlace_html = escape(enlace, quote=True)

    html = f"""\
<!doctype html>
<html lang="es">
<body style="margin:0;padding:0;background:{COLOR_FONDO};font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{COLOR_FONDO};padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border-radius:12px;overflow:hidden;">
        <tr><td style="background:{COLOR_MARCA};padding:24px;text-align:center;color:#ffffff;font-size:24px;font-weight:bold;letter-spacing:1px;">
          Estetika Elora
        </td></tr>
        <tr><td style="padding:32px 32px 8px;color:#333333;font-size:16px;line-height:1.6;">
          <p style="margin:0 0 16px;font-size:20px;font-weight:bold;color:{COLOR_MARCA_OSCURO};">¡Hola, {nombre_html}!</p>
          <p style="margin:0 0 24px;">Gracias por registrarte en Estetika Elora. Para empezar a reservar servicios y comprar productos, activa tu cuenta:</p>
        </td></tr>
        <tr><td align="center" style="padding:0 32px 24px;">
          <a href="{enlace_html}" style="display:inline-block;background:{COLOR_MARCA};color:#ffffff;text-decoration:none;font-weight:bold;font-size:16px;padding:14px 32px;border-radius:8px;">Activar mi cuenta</a>
        </td></tr>
        <tr><td style="padding:0 32px 32px;color:#555555;font-size:14px;line-height:1.6;">
          <p style="margin:0 0 16px;">Este enlace vence en {vigencia_horas} horas.</p>
          <p style="margin:0 0 16px;">Si el botón no funciona, copia este enlace en tu navegador:<br>
            <a href="{enlace_html}" style="color:{COLOR_MARCA_OSCURO};word-break:break-all;">{enlace_html}</a></p>
          <p style="margin:0;color:#888888;">Si no creaste esta cuenta, ignora este mensaje.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    texto = (
        f"¡Hola, {primer_nombre}!\n\n"
        "Gracias por registrarte en Estetika Elora. Para empezar a reservar servicios y comprar "
        "productos, activa tu cuenta abriendo este enlace:\n\n"
        f"{enlace}\n\n"
        f"Este enlace vence en {vigencia_horas} horas.\n"
        "Si no creaste esta cuenta, ignora este mensaje."
    )

    return Correo(
        destinatario=destinatario,
        nombre_destinatario=nombre,
        asunto="Activa tu cuenta en Estetika Elora",
        html=html,
        texto=texto,
    )
