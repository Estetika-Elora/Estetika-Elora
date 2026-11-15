"""Seguridad de cuentas: hash de contraseñas y tokens de un solo uso.

- Contraseñas: se guardan con bcrypt (hash de una sola vía con sal). No se pueden revertir;
  para el login (HU-02) se compara con `verificar_contrasena`.
- Tokens de verificación: aleatorios (256 bits) e imposibles de adivinar. Al usuario se le
  envía el token; en el repositorio solo se guarda su hash SHA-256.
"""

import hashlib
import secrets

import bcrypt


def hashear_contrasena(contrasena: str) -> str:
    return bcrypt.hashpw(contrasena.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_contrasena(contrasena: str, contrasena_hash: str) -> bool:
    return bcrypt.checkpw(contrasena.encode("utf-8"), contrasena_hash.encode("utf-8"))


def generar_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
