"""Contraseña de acceso. Se guarda solo un hash con sal, nunca la clave en sí."""
import hashlib
import hmac
import secrets

from database import ajustes

ITERACIONES = 200_000


def _hash(clave, sal_hex):
    return hashlib.pbkdf2_hmac(
        "sha256", clave.encode("utf-8"), bytes.fromhex(sal_hex), ITERACIONES
    ).hex()


def hay_clave():
    return ajustes.obtener("clave_hash") is not None


def establecer_clave(clave):
    sal = secrets.token_hex(16)
    ajustes.guardar_varios({"clave_sal": sal, "clave_hash": _hash(clave, sal)})


def verificar_clave(clave):
    sal = ajustes.obtener("clave_sal")
    guardado = ajustes.obtener("clave_hash")
    if not sal or not guardado:
        return False
    return hmac.compare_digest(_hash(clave, sal), guardado)
