import sqlite3

from config import RUTA_BD

# Ruta absoluta: siempre la base que está en la carpeta del proyecto.
DB = str(RUTA_BD)


def conectar():
    conn = sqlite3.connect(DB)

    # Activar claves foráneas
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def _columnas(cursor, tabla):
    return [fila[1] for fila in cursor.execute(f"PRAGMA table_info({tabla})")]


def inicializar_bd():

    conn = conectar()
    cursor = conn.cursor()

    # Tabla docentes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS docentes (
            id_docente INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            dni INTEGER NOT NULL UNIQUE,
            cuil INTEGER NOT NULL UNIQUE,
            fecha_nacimiento TEXT NOT NULL,
            domicilio TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            caracter TEXT NOT NULL,
            activo INTEGER NOT NULL DEFAULT 1
        )
    """)

    # Tabla carrera
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS carrera (
            id_carrera INTEGER PRIMARY KEY AUTOINCREMENT,
            nom_carrera TEXT NOT NULL,
            cant_materias INTEGER NOT NULL,
            resolucion TEXT NOT NULL
        )
    """)

    # Tabla materia
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS materia (
            id_materia INTEGER PRIMARY KEY AUTOINCREMENT,
            materia_id INTEGER NOT NULL,
            nom_materia TEXT NOT NULL,
            cant_horas INTEGER NOT NULL,
            id_carrera INTEGER NOT NULL,
            FOREIGN KEY (id_carrera)
                REFERENCES carrera(id_carrera)
        )
    """)

    # Tabla designacion
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS designacion (
            id_docente_materia INTEGER PRIMARY KEY AUTOINCREMENT,
            id_docente INTEGER NOT NULL,
            id_materia INTEGER NOT NULL,
            fecha_alta TEXT NOT NULL,
            fecha_baja TEXT,
            motivo_baja TEXT,
            estado TEXT NOT NULL,
            nro_disposicion TEXT NOT NULL,
            FOREIGN KEY (id_docente)
                REFERENCES docentes(id_docente),
            FOREIGN KEY (id_materia)
                REFERENCES materia(id_materia)
        )
    """)

    # Tabla certificado_medico
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS certificado_medico (
            id_certificado INTEGER PRIMARY KEY AUTOINCREMENT,
            id_docente INTEGER NOT NULL,
            fecha_emision TEXT NOT NULL,
            fecha_inicio TEXT NOT NULL,
            dias INTEGER NOT NULL,
            medico TEXT NOT NULL,
            matricula TEXT,
            observaciones TEXT,
            FOREIGN KEY (id_docente)
                REFERENCES docentes(id_docente)
                ON DELETE CASCADE
        )
    """)

    # Tabla licencia (licencias del docente que no son carpeta médica)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS licencia (
            id_licencia INTEGER PRIMARY KEY AUTOINCREMENT,
            id_docente INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            fecha_desde TEXT NOT NULL,
            fecha_hasta TEXT NOT NULL,
            observaciones TEXT,
            FOREIGN KEY (id_docente)
                REFERENCES docentes(id_docente)
                ON DELETE CASCADE
        )
    """)

    # Tabla suplencia: une la designación del titular con la del suplente que lo cubre
    # (la del suplente es una designación normal, con situación "S").
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suplencia (
            id_suplencia INTEGER PRIMARY KEY AUTOINCREMENT,
            id_designacion_titular INTEGER NOT NULL,
            id_designacion_suplente INTEGER NOT NULL UNIQUE,
            motivo TEXT,
            FOREIGN KEY (id_designacion_titular)
                REFERENCES designacion(id_docente_materia) ON DELETE CASCADE,
            FOREIGN KEY (id_designacion_suplente)
                REFERENCES designacion(id_docente_materia) ON DELETE CASCADE
        )
    """)

    # Libro de constancias emitidas (se guarda el PDF para reimprimirlo igual)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS constancia_emitida (
            id_constancia INTEGER PRIMARY KEY AUTOINCREMENT,
            anio INTEGER NOT NULL,
            numero INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            id_docente INTEGER,
            docente TEXT NOT NULL,
            dni TEXT NOT NULL,
            fecha TEXT NOT NULL,
            detalle TEXT,
            pdf BLOB,
            UNIQUE (anio, numero)
        )
    """)

    # Tabla configuracion (datos de la institución, contraseña, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    """)

    # Migración: datos nuevos de las designaciones (columnas de la constancia de trabajo)
    columnas = _columnas(cursor, "designacion")
    for columna in ("turno", "situacion", "anio", "division", "condicion", "tipo_designacion"):
        if columna not in columnas:
            cursor.execute(f"ALTER TABLE designacion ADD COLUMN {columna} TEXT")

    # Migración: datos de la solicitud de licencia médica
    columnas = _columnas(cursor, "certificado_medico")
    for columna in ("tipo_pedido", "parentesco", "funcion", "horario", "numero_constancia"):
        if columna not in columnas:
            cursor.execute(f"ALTER TABLE certificado_medico ADD COLUMN {columna} TEXT")

    # Migración: bases creadas antes de existir la columna "activo"
    if "activo" not in _columnas(cursor, "docentes"):
        cursor.execute(
            "ALTER TABLE docentes ADD COLUMN activo INTEGER NOT NULL DEFAULT 1"
        )

    conn.commit()
    conn.close()
