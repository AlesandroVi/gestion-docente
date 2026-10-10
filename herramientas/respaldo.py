"""Copias de seguridad de Gestion.db."""
import sqlite3
from datetime import datetime
from pathlib import Path

from config import COPIAS_AUTOMATICAS_A_CONSERVAR, CARPETA_COPIAS
from database.conexion import DB


def hacer_copia(carpeta_destino, prefijo="Gestion"):
    """Guarda una copia con fecha y hora en `carpeta_destino`. Devuelve la ruta del archivo.

    Usa la API de copia de SQLite, que es segura aunque la base esté en uso.
    """
    carpeta = Path(carpeta_destino).expanduser()
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / f"{prefijo}_{datetime.now():%Y-%m-%d_%H-%M-%S}.db"

    origen = sqlite3.connect(DB)
    copia = sqlite3.connect(str(destino))
    try:
        origen.backup(copia)
    finally:
        copia.close()
        origen.close()
    return destino


def listar_copias(carpeta=CARPETA_COPIAS):
    carpeta = Path(carpeta)
    if not carpeta.exists():
        return []
    return sorted(carpeta.glob("Auto_*.db"), reverse=True)


def copia_automatica():
    """Una copia por día, en la carpeta del proyecto. Conserva solo las más recientes."""
    hoy = f"Auto_{datetime.now():%Y-%m-%d}"
    if any(c.name.startswith(hoy) for c in listar_copias()):
        return None
    ruta = hacer_copia(CARPETA_COPIAS, prefijo="Auto")
    for vieja in listar_copias()[COPIAS_AUTOMATICAS_A_CONSERVAR:]:
        try:
            vieja.unlink()
        except OSError:
            pass
    return ruta
