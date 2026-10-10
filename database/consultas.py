"""Consultas y utilidades de fechas compartidas por varias pantallas."""
import sqlite3
from datetime import date, datetime

from database.conexion import conectar

FORMATO_FECHA = "%d/%m/%Y"


def parse_fecha(texto):
    """'dd/mm/aaaa' -> date, o None si no tiene ese formato."""
    try:
        return datetime.strptime(str(texto).strip(), FORMATO_FECHA).date()
    except (ValueError, TypeError):
        return None


def es_vigente(baja, hoy=None):
    """Una designación está vigente si no tiene baja o la baja todavía no pasó."""
    if not baja:
        return True
    fecha = parse_fecha(baja)
    if fecha is None:
        return False
    return fecha >= (hoy or date.today())


def estado_designacion(baja, hoy=None):
    if not baja:
        return "Vigente"
    if es_vigente(baja, hoy):
        return f"Vigente hasta {baja}"
    return "Baja"


def listar_docentes(filtro="", incluir_inactivos=True):
    """Filas: dni, nombre, apellido, cuil, nacimiento, domicilio, email, carácter, activo."""
    patron = f"%{(filtro or '').strip()}%"
    sql = (
        "SELECT dni, nombre, apellido, cuil, fecha_nacimiento, domicilio, email, caracter, activo "
        "FROM docentes "
        "WHERE (CAST(dni AS TEXT) LIKE ? OR nombre LIKE ? OR apellido LIKE ? "
        "OR apellido || ' ' || nombre LIKE ? OR nombre || ' ' || apellido LIKE ?)"
    )
    if not incluir_inactivos:
        sql += " AND activo = 1"
    sql += " ORDER BY apellido, nombre"

    conexion = conectar()
    try:
        return conexion.execute(sql, (patron,) * 5).fetchall()
    except sqlite3.Error as error:
        print("Error al cargar docentes:", error)
        return []
    finally:
        conexion.close()


def contar_docentes_activos():
    conexion = conectar()
    try:
        return conexion.execute("SELECT COUNT(*) FROM docentes WHERE activo = 1").fetchone()[0]
    finally:
        conexion.close()


def designaciones_de(dni):
    """(materia, carrera, estado, alta, baja, disposición), de la más antigua a la más nueva."""
    conexion = conectar()
    try:
        filas = conexion.execute(
            "SELECT m.nom_materia, c.nom_carrera, de.fecha_alta, de.fecha_baja, de.nro_disposicion "
            "FROM designacion de "
            "JOIN docentes doc ON doc.id_docente = de.id_docente "
            "JOIN materia m ON m.id_materia = de.id_materia "
            "JOIN carrera c ON c.id_carrera = m.id_carrera "
            "WHERE doc.dni = ?",
            (dni,),
        ).fetchall()
    except sqlite3.Error as error:
        print("Error al cargar designaciones:", error)
        return []
    finally:
        conexion.close()

    filas.sort(key=lambda f: parse_fecha(f[2]) or date.min)
    return [(m, c, estado_designacion(baja), alta, baja, disp) for m, c, alta, baja, disp in filas]


def certificados_de(dni):
    """(id, fecha_emision, fecha_inicio, dias, medico, matricula, observaciones,
    tipo_pedido, parentesco, funcion, horario, numero_constancia), el más nuevo primero."""
    conexion = conectar()
    try:
        return conexion.execute(
            "SELECT cm.id_certificado, cm.fecha_emision, cm.fecha_inicio, cm.dias, "
            "cm.medico, cm.matricula, cm.observaciones, "
            "cm.tipo_pedido, cm.parentesco, cm.funcion, cm.horario, cm.numero_constancia "
            "FROM certificado_medico cm "
            "JOIN docentes doc ON doc.id_docente = cm.id_docente "
            "WHERE doc.dni = ? ORDER BY cm.id_certificado DESC",
            (dni,),
        ).fetchall()
    except sqlite3.Error as error:
        print("Error al cargar certificados:", error)
        return []
    finally:
        conexion.close()


def designaciones_detalle(dni):
    """Para la ficha del docente:
    (materia, carrera, horas, alta, baja, disposición, motivo de baja, vigente),
    primero las vigentes y después las demás (de la más nueva a la más vieja)."""
    conexion = conectar()
    try:
        filas = conexion.execute(
            "SELECT m.nom_materia, c.nom_carrera, m.cant_horas, de.fecha_alta, de.fecha_baja, "
            "de.nro_disposicion, de.motivo_baja "
            "FROM designacion de "
            "JOIN docentes doc ON doc.id_docente = de.id_docente "
            "JOIN materia m ON m.id_materia = de.id_materia "
            "JOIN carrera c ON c.id_carrera = m.id_carrera "
            "WHERE doc.dni = ?",
            (dni,),
        ).fetchall()
    except sqlite3.Error as error:
        print("Error al cargar designaciones:", error)
        return []
    finally:
        conexion.close()

    resultado = [f + (es_vigente(f[4]),) for f in filas]
    resultado.sort(key=lambda f: parse_fecha(f[3]) or date.min, reverse=True)
    resultado.sort(key=lambda f: not f[7])
    return resultado


def licencias_de(dni):
    """(id, tipo, desde, hasta, observaciones), la más nueva primero."""
    conexion = conectar()
    try:
        filas = conexion.execute(
            "SELECT l.id_licencia, l.tipo, l.fecha_desde, l.fecha_hasta, l.observaciones "
            "FROM licencia l JOIN docentes doc ON doc.id_docente = l.id_docente "
            "WHERE doc.dni = ?",
            (dni,),
        ).fetchall()
    except sqlite3.Error as error:
        print("Error al cargar licencias:", error)
        return []
    finally:
        conexion.close()
    filas.sort(key=lambda f: parse_fecha(f[2]) or date.min, reverse=True)
    return filas


def designaciones_constancia(dni):
    """Filas para la tabla de la constancia de trabajo (diccionarios), por fecha de alta."""
    conexion = conectar()
    conexion.row_factory = sqlite3.Row
    try:
        filas = conexion.execute(
            "SELECT m.nom_materia AS materia, c.nom_carrera AS carrera, c.resolucion, "
            "m.cant_horas AS horas, de.fecha_alta AS alta, de.fecha_baja AS baja, "
            "de.nro_disposicion AS disposicion, de.motivo_baja, de.turno, de.situacion, "
            "de.anio, de.division, de.condicion, de.tipo_designacion "
            "FROM designacion de "
            "JOIN docentes doc ON doc.id_docente = de.id_docente "
            "JOIN materia m ON m.id_materia = de.id_materia "
            "JOIN carrera c ON c.id_carrera = m.id_carrera "
            "WHERE doc.dni = ?",
            (dni,),
        ).fetchall()
    except sqlite3.Error as error:
        print("Error al cargar designaciones:", error)
        return []
    finally:
        conexion.close()
    resultado = [dict(f) for f in filas]
    resultado.sort(key=lambda f: parse_fecha(f["alta"]) or date.min)
    return resultado
