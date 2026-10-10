"""Lectura y escritura de la tabla `configuracion` (clave -> valor)."""
from config import INSTITUCION_PREDETERMINADA
from database.conexion import conectar


def obtener(clave, predeterminado=None):
    con = conectar()
    try:
        fila = con.execute(
            "SELECT valor FROM configuracion WHERE clave = ?", (clave,)
        ).fetchone()
    finally:
        con.close()
    if fila is not None:
        return fila[0]
    return INSTITUCION_PREDETERMINADA.get(clave, predeterminado)


def guardar(clave, valor):
    guardar_varios({clave: valor})


def guardar_varios(valores):
    con = conectar()
    try:
        with con:
            for clave, valor in valores.items():
                con.execute(
                    "INSERT INTO configuracion (clave, valor) VALUES (?, ?) "
                    "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
                    (clave, str(valor)),
                )
    finally:
        con.close()


def institucion():
    """Datos de la institución (con sus valores iniciales si no se cambiaron)."""
    return {clave: obtener(clave) for clave in INSTITUCION_PREDETERMINADA}


def restaurar_institucion():
    con = conectar()
    try:
        with con:
            con.executemany(
                "DELETE FROM configuracion WHERE clave = ?",
                [(c,) for c in INSTITUCION_PREDETERMINADA],
            )
    finally:
        con.close()


def borrar_clave_acceso():
    con = conectar()
    try:
        with con:
            con.execute("DELETE FROM configuracion WHERE clave IN ('clave_hash', 'clave_sal')")
    finally:
        con.close()
