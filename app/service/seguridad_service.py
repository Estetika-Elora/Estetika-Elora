"""Seguridad de cuentas: hash de contraseñas, tokens de un solo uso y tokens de acceso JWT.

- Contraseñas: se guardan con bcrypt (hash de una sola vía con sal). No se pueden revertir;
  para el login (HU-02) se compara con `verificar_contrasena`.
- Tokens de verificación: aleatorios (256 bits) e imposibles de adivinar. Al usuario se le
  envía el token; en el repositorio solo se guarda su hash SHA-256.
- Tokens de acceso (HU-02): JWT firmado con HS256 y la SECRET_KEY. Lleva el id del usuario
  (`sub`), su rol y el vencimiento (`exp`); no se guarda en el servidor.
"""

import hashlib
import secrets
from datetime import datetime, timedelta

import bcrypt
import jwt

ALGORITMO_JWT = "HS256"


def hashear_contrasena(contrasena: str) -> str:
    return bcrypt.hashpw(contrasena.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_contrasena(contrasena: str, contrasena_hash: str) -> bool:
    return bcrypt.checkpw(contrasena.encode("utf-8"), contrasena_hash.encode("utf-8"))


def generar_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def crear_token_acceso(usuario_id: int, rol: str, secreto: str, emitido_en: datetime, minutos: int) -> str:
    datos = {
        "sub": str(usuario_id),
        "rol": rol,
        "iat": emitido_en,
        "exp": emitido_en + timedelta(minutes=minutos),
    }
    return jwt.encode(datos, secreto, algorithm=ALGORITMO_JWT)
