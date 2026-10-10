"""Libro de constancias emitidas: cada constancia lleva un número correlativo por año
(ej: 15/2026) y se guarda el PDF tal cual salió, para reimprimirlo igual."""
import sqlite3
from datetime import date

from database.conexion import conectar
from database.consultas import FORMATO_FECHA

TIPOS = ["Trabajo", "Examen", "Licencia médica"]


def siguiente_numero(anio=None):
    anio = anio or date.today().year
    conexion = conectar()
    try:
        ultimo = conexion.execute(
            "SELECT MAX(numero) FROM constancia_emitida WHERE anio = ?", (anio,)).fetchone()[0]
    finally:
        conexion.close()
    return (ultimo or 0) + 1, anio


def texto_numero(numero, anio):
    return f"{numero}/{anio}"


def emitir(tipo, d, ruta, construir, detalle=""):
    """Reserva el número, arma el PDF con `construir(texto_del_numero)` y lo guarda en el libro.
    `d` es la fila del docente. Devuelve el número como texto (ej: '15/2026')."""
    numero, anio = siguiente_numero()
    etiqueta = texto_numero(numero, anio)
    construir(etiqueta)
    with open(ruta, "rb") as archivo:
        pdf = archivo.read()

    conexion = conectar()
    try:
        with conexion:
            fila = conexion.execute("SELECT id_docente FROM docentes WHERE dni = ?", (d[0],)).fetchone()
            conexion.execute(
                "INSERT INTO constancia_emitida (anio, numero, tipo, id_docente, docente, dni, "
                "fecha, detalle, pdf) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (anio, numero, tipo, fila[0] if fila else None, f"{d[2]}, {d[1]}", str(d[0]),
                 date.today().strftime(FORMATO_FECHA), detalle, sqlite3.Binary(pdf)))
    finally:
        conexion.close()
    return etiqueta


def listar(filtro="", tipo=None):
    """[(id, número, año, fecha, tipo, docente, dni, detalle)], la más nueva primero."""
    patron = f"%{(filtro or '').strip()}%"
    sql = ("SELECT id_constancia, numero, anio, fecha, tipo, docente, dni, detalle "
           "FROM constancia_emitida WHERE (docente LIKE ? OR dni LIKE ? OR detalle LIKE ? "
           "OR (numero || '/' || anio) LIKE ?)")
    parametros = [patron] * 4
    if tipo:
        sql += " AND tipo = ?"
        parametros.append(tipo)
    conexion = conectar()
    try:
        return conexion.execute(sql + " ORDER BY anio DESC, numero DESC", parametros).fetchall()
    finally:
        conexion.close()


def guardar_copia(id_constancia, carpeta):
    """Escribe el PDF guardado en `carpeta` y devuelve la ruta."""
    conexion = conectar()
    try:
        fila = conexion.execute(
            "SELECT numero, anio, tipo, dni, pdf FROM constancia_emitida WHERE id_constancia = ?",
            (id_constancia,)).fetchone()
    finally:
        conexion.close()
    if not fila or not fila[4]:
        raise FileNotFoundError("La constancia no tiene el PDF guardado.")
    numero, anio, tipo, dni, pdf = fila
    nombre = f"constancia_{tipo.lower().replace(' ', '_').replace('é', 'e')}_{numero}-{anio}_{dni}.pdf"
    ruta = carpeta / nombre
    with open(ruta, "wb") as archivo:
        archivo.write(pdf)
    return ruta
