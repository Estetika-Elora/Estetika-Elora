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


def correo_recuperacion_contrasena(destinatario: str, nombre: str, codigo: str, vigencia_minutos: int) -> Correo:
    primer_nombre = nombre.split()[0]
    nombre_html = escape(primer_nombre)
    codigo_html = escape(codigo)

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
          <p style="margin:0 0 24px;">Recibimos una solicitud para restablecer la contraseña de tu cuenta. Usa este código para definir una contraseña nueva:</p>
        </td></tr>
        <tr><td align="center" style="padding:0 32px 24px;">
          <div style="display:inline-block;background:{COLOR_FONDO};color:{COLOR_MARCA_OSCURO};font-size:32px;font-weight:bold;letter-spacing:8px;padding:16px 32px;border-radius:8px;">{codigo_html}</div>
        </td></tr>
        <tr><td style="padding:0 32px 32px;color:#555555;font-size:14px;line-height:1.6;">
          <p style="margin:0 0 16px;">Este código vence en {vigencia_minutos} minutos y solo se puede usar una vez.</p>
          <p style="margin:0;color:#888888;">Si no solicitaste este cambio, ignora este mensaje: tu contraseña actual sigue funcionando.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    texto = (
        f"¡Hola, {primer_nombre}!\n\n"
        "Recibimos una solicitud para restablecer la contraseña de tu cuenta en Estetika Elora. "
        "Usa este código para definir una contraseña nueva:\n\n"
        f"{codigo}\n\n"
        f"Este código vence en {vigencia_minutos} minutos y solo se puede usar una vez.\n"
        "Si no solicitaste este cambio, ignora este mensaje: tu contraseña actual sigue funcionando."
    )

    return Correo(
        destinatario=destinatario,
        nombre_destinatario=nombre,
        asunto="Código para restablecer tu contraseña en Estetika Elora",
        html=html,
        texto=texto,
    )


def correo_reserva_confirmada(
    destinatario: str, nombre: str, reserva_id: int, sede: str, servicio: str, fecha: str, hora: str
) -> Correo:
    primer_nombre = nombre.split()[0]
    filas = [("Reserva", f"#{reserva_id}"), ("Servicio", servicio), ("Sede", sede), ("Fecha", fecha), ("Hora", hora)]
    filas_html = "".join(
        f'<tr><td style="padding:6px 0;color:#888888;width:35%;">{escape(etiqueta)}</td>'
        f'<td style="padding:6px 0;font-weight:bold;">{escape(valor)}</td></tr>'
        for etiqueta, valor in filas
    )

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
          <p style="margin:0 0 16px;font-size:20px;font-weight:bold;color:{COLOR_MARCA_OSCURO};">¡Hola, {escape(primer_nombre)}!</p>
          <p style="margin:0 0 16px;">Tu reserva quedó confirmada. Estos son los detalles:</p>
        </td></tr>
        <tr><td style="padding:0 32px 24px;color:#333333;font-size:15px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{filas_html}</table>
        </td></tr>
        <tr><td style="padding:0 32px 32px;color:#888888;font-size:14px;line-height:1.6;">
          <p style="margin:0;">Te esperamos. Si no hiciste esta reserva, comunícate con nosotros.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    detalle = "\n".join(f"{etiqueta}: {valor}" for etiqueta, valor in filas)
    texto = (
        f"¡Hola, {primer_nombre}!\n\n"
        "Tu reserva quedó confirmada. Estos son los detalles:\n\n"
        f"{detalle}\n\n"
        "Te esperamos. Si no hiciste esta reserva, comunícate con nosotros."
    )

    return Correo(
        destinatario=destinatario,
        nombre_destinatario=nombre,
        asunto=f"Reserva confirmada: {servicio} el {fecha} a las {hora}",
        html=html,
        texto=texto,
    )


def correo_solicitud_empresa_recibida(
    destinatario: str,
    nombre: str,
    razon_social: str,
    nit: str,
) -> Correo:
    """Confirma al representante que la solicitud fue recibida."""

    primer_nombre = escape(nombre.split()[0] if nombre.split() else nombre)

    razon_social_html = escape(razon_social)
    nit_html = escape(nit)

    html = f"""
    <!doctype html>
    <html lang="es">
    <body style="font-family: Arial; padding: 25px;">
        <h2>¡Hola, {primer_nombre}!</h2>

        <p>
            Hemos recibido la solicitud para registrar tu empresa
            en Estetika Elora.
        </p>

        <p><strong>Razón social:</strong> {razon_social_html}</p>
        <p><strong>NIT:</strong> {nit_html}</p>

        <p>
            Tu solicitud quedó en estado
            <strong>PENDIENTE DE APROBACIÓN</strong>.
        </p>

        <p>
            Te notificaremos cuando termine el proceso de revisión.
        </p>
    </body>
    </html>
    """

    texto = (
        f"¡Hola, {nombre}!\n\n"
        "Hemos recibido tu solicitud de registro en Estetika Elora.\n\n"
        f"Razón social: {razon_social}\n"
        f"NIT: {nit}\n"
        "Estado: PENDING_APPROVAL.\n\n"
        "Te notificaremos cuando termine el proceso de revisión."
    )

    return Correo(
        destinatario=destinatario,
        nombre_destinatario=nombre,
        asunto="Solicitud de registro recibida - Estetika Elora",
        html=html,
        texto=texto,
    )
