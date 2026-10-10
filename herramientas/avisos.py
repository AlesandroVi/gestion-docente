"""Avisos del inicio: reposos vigentes y designaciones por vencer."""
from datetime import date, timedelta

from config import DIAS_AVISO_VENCIMIENTO
from database.conexion import conectar
from database.consultas import parse_fecha


def reposos_vigentes(hoy=None):
    """Docentes activos con un certificado médico cuyo reposo incluye hoy.
    Devuelve [(apellido y nombre, dni, desde, hasta, días que faltan)]."""
    hoy = hoy or date.today()
    conexion = conectar()
    try:
        filas = conexion.execute(
            "SELECT d.apellido, d.nombre, d.dni, c.fecha_inicio, c.dias "
            "FROM certificado_medico c JOIN docentes d ON d.id_docente = c.id_docente "
            "WHERE d.activo = 1").fetchall()
    finally:
        conexion.close()

    resultado = []
    for apellido, nombre, dni, inicio, dias in filas:
        desde = parse_fecha(inicio)
        if desde is None:
            continue
        hasta = desde + timedelta(days=dias - 1)
        if desde <= hoy <= hasta:
            resultado.append((f"{apellido}, {nombre}", dni, desde, hasta, (hasta - hoy).days))
    return sorted(resultado, key=lambda r: r[3])


def designaciones_por_vencer(dias=DIAS_AVISO_VENCIMIENTO, hoy=None):
    """Designaciones con baja programada en los próximos `dias` días.
    Devuelve [(apellido y nombre, materia, carrera, fecha de baja, días que faltan)]."""
    hoy = hoy or date.today()
    limite = hoy + timedelta(days=dias)
    conexion = conectar()
    try:
        filas = conexion.execute(
            "SELECT d.apellido, d.nombre, m.nom_materia, c.nom_carrera, de.fecha_baja "
            "FROM designacion de "
            "JOIN docentes d ON d.id_docente = de.id_docente "
            "JOIN materia m ON m.id_materia = de.id_materia "
            "JOIN carrera c ON c.id_carrera = m.id_carrera "
            "WHERE d.activo = 1 AND de.fecha_baja IS NOT NULL AND de.fecha_baja != ''").fetchall()
    finally:
        conexion.close()

    resultado = []
    for apellido, nombre, materia, carrera, baja in filas:
        fecha = parse_fecha(baja)
        if fecha is not None and hoy <= fecha <= limite:
            resultado.append((f"{apellido}, {nombre}", materia, carrera, fecha, (fecha - hoy).days))
    return sorted(resultado, key=lambda r: r[3])


def licencias_vigentes(hoy=None):
    """Licencias (no médicas) de docentes activos que incluyen hoy.
    Devuelve [(apellido y nombre, dni, tipo, desde, hasta, días que faltan)]."""
    hoy = hoy or date.today()
    conexion = conectar()
    try:
        filas = conexion.execute(
            "SELECT d.apellido, d.nombre, d.dni, l.tipo, l.fecha_desde, l.fecha_hasta "
            "FROM licencia l JOIN docentes d ON d.id_docente = l.id_docente "
            "WHERE d.activo = 1").fetchall()
    finally:
        conexion.close()

    resultado = []
    for apellido, nombre, dni, tipo, desde, hasta in filas:
        d1, d2 = parse_fecha(desde), parse_fecha(hasta)
        if d1 and d2 and d1 <= hoy <= d2:
            resultado.append((f"{apellido}, {nombre}", dni, tipo, d1, d2, (d2 - hoy).days))
    return sorted(resultado, key=lambda r: r[4])


def ausentes_hoy(hoy=None):
    """{id_docente: (motivo, hasta)} de quienes hoy tienen licencia o carpeta médica."""
    hoy = hoy or date.today()
    conexion = conectar()
    try:
        licencias = conexion.execute(
            "SELECT id_docente, tipo, fecha_desde, fecha_hasta FROM licencia").fetchall()
        reposos = conexion.execute(
            "SELECT id_docente, fecha_inicio, dias FROM certificado_medico").fetchall()
    finally:
        conexion.close()

    ausentes = {}

    def anotar(id_docente, motivo, hasta):
        # Si tiene más de una, se queda con la que termina más tarde
        if id_docente not in ausentes or ausentes[id_docente][1] < hasta:
            ausentes[id_docente] = (motivo, hasta)

    for id_docente, tipo, desde, hasta in licencias:
        d1, d2 = parse_fecha(desde), parse_fecha(hasta)
        if d1 and d2 and d1 <= hoy <= d2:
            anotar(id_docente, f"Licencia: {tipo}", d2)
    for id_docente, inicio, dias in reposos:
        d1 = parse_fecha(inicio)
        if d1:
            d2 = d1 + timedelta(days=dias - 1)
            if d1 <= hoy <= d2:
                anotar(id_docente, "Carpeta médica", d2)
    return ausentes
