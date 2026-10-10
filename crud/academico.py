"""Carga de carreras, materias y designaciones de docentes."""
import sqlite3
from datetime import date

import flet as ft

from config import ANIOS, CONDICIONES, SITUACIONES, TIPOS_DESIGNACION, TURNOS
from database.conexion import conectar
from database.consultas import FORMATO_FECHA, estado_designacion, es_vigente, parse_fecha
from ui import (
    actualizar_opciones, autolimpiar, avisar, campo, campo_fecha, cerrar_dialogo, confirmar,
    desplegable, encabezado_seccion, mostrar_mensaje, ocultar_error_al_escribir, solo_numeros,
    poner_error, tarjeta_formulario,
)

COLOR_CARRERAS = ft.Colors.INDIGO_700
COLOR_MATERIAS = ft.Colors.TEAL_700
COLOR_DESIGNACIONES = ft.Colors.PURPLE_700


# ---------- ACCESO A DATOS ----------

def _consultar(sql, params=()):
    conexion = conectar()
    try:
        return conexion.execute(sql, params).fetchall()
    except sqlite3.Error as error:
        print("Error de consulta:", error)
        return []
    finally:
        conexion.close()


def _ejecutar(sql, params=()):
    """Ejecuta una escritura. Devuelve (ok, id_insertado)."""
    conexion = conectar()
    try:
        with conexion:
            cursor = conexion.execute(sql, params)
        return True, cursor.lastrowid
    except sqlite3.Error as error:
        print("Error al escribir:", error)
        return False, None
    finally:
        conexion.close()


def _numero_positivo(texto):
    texto = (texto or "").strip()
    return int(texto) if texto.isdigit() and int(texto) > 0 else None


def _tabla_centrada(tabla):
    return ft.Row(controls=[tabla], alignment=ft.MainAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO)


def _columna(controles):
    return ft.Column(controls=controles, scroll=ft.ScrollMode.AUTO, spacing=18,
                     horizontal_alignment=ft.CrossAxisAlignment.STRETCH)


def _lista(titulo, icono, color, controles):
    """Tarjeta con franja de color que contiene un listado o una tabla."""
    return ft.Container(
        content=ft.Column(
            controls=[
                encabezado_seccion(titulo, icono, color),
                ft.Container(content=ft.Column(controls=controles, spacing=12), padding=18),
            ],
            spacing=0,
        ),
        border_radius=12,
        border=ft.Border.all(1, ft.Colors.GREY_300),
    )


# =====================================================================
#  CARRERAS
# =====================================================================

def _validar_carrera(nombre, cantidad, resolucion, id_actual=0):
    errores = {}
    nombre = " ".join((nombre or "").split())
    resolucion = (resolucion or "").strip()
    cant = _numero_positivo(cantidad)

    if not nombre:
        errores["nombre"] = "Ingresá el nombre de la carrera."
    elif _consultar("SELECT 1 FROM carrera WHERE lower(nom_carrera) = lower(?) AND id_carrera != ?",
                    (nombre, id_actual)):
        errores["nombre"] = "Ya existe una carrera con ese nombre."
    if cant is None:
        errores["cantidad"] = "Ingresá un número mayor a 0."
    if not resolucion:
        errores["resolucion"] = "Ingresá la resolución."
    return errores, (nombre, cant, resolucion)


def _tab_carreras(page, refrescar_todo, registrar):
    nombre = campo("Nombre de la carrera", ft.Icons.SCHOOL, 380)
    cantidad = campo("Materias del plan", ft.Icons.FORMAT_LIST_NUMBERED, 190, max_length=3,
                     input_filter=solo_numeros(), keyboard_type=ft.KeyboardType.NUMBER)
    resolucion = campo("Resolución", ft.Icons.GAVEL, 240)
    campos = {"nombre": nombre, "cantidad": cantidad, "resolucion": resolucion}
    autolimpiar(nombre, cantidad, resolucion)

    tabla = ft.DataTable(columns=[
        ft.DataColumn(label=ft.Text("Carrera")),
        ft.DataColumn(label=ft.Text("Materias del plan")),
        ft.DataColumn(label=ft.Text("Materias cargadas")),
        ft.DataColumn(label=ft.Text("Resolución")),
        ft.DataColumn(label=ft.Text("Acciones")),
    ], rows=[])
    vacio = ft.Text("Todavía no hay carreras cargadas.", color=ft.Colors.GREY_600)

    def cargar():
        filas = _consultar(
            "SELECT c.id_carrera, c.nom_carrera, c.cant_materias, c.resolucion, "
            "(SELECT COUNT(*) FROM materia m WHERE m.id_carrera = c.id_carrera) "
            "FROM carrera c ORDER BY c.nom_carrera")
        tabla.rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(f[1])),
                ft.DataCell(ft.Text(str(f[2]))),
                ft.DataCell(ft.Text(str(f[4]))),
                ft.DataCell(ft.Text(f[3])),
                ft.DataCell(ft.Row(spacing=0, controls=[
                    ft.IconButton(icon=ft.Icons.EDIT, tooltip="Modificar",
                                  on_click=lambda e, fila=f: editar(fila)),
                    ft.IconButton(icon=ft.Icons.DELETE, tooltip="Eliminar",
                                  on_click=lambda e, fila=f: eliminar(fila)),
                ])),
            ]) for f in filas
        ]
        tabla.visible = bool(filas)
        vacio.visible = not filas
        page.update()

    def agregar(e):
        errores, (n, c, r) = _validar_carrera(nombre.value, cantidad.value, resolucion.value)
        for clave, campo in campos.items():
            poner_error(campo, errores.get(clave))
        if errores:
            page.update()
            return
        ok, _ = _ejecutar("INSERT INTO carrera (nom_carrera, cant_materias, resolucion) VALUES (?, ?, ?)",
                          (n, c, r))
        if not ok:
            return avisar(page, "No se pudo guardar la carrera.")
        for campo in campos.values():
            campo.value = ""
        refrescar_todo()
        avisar(page, f"Carrera «{n}» guardada correctamente.")

    def editar(f):
        ancho = 400
        n = ft.TextField(label="Nombre de la carrera", value=f[1], width=ancho)
        c = ft.TextField(label="Materias del plan", value=str(f[2]), width=ancho, max_length=3,
                         input_filter=solo_numeros())
        r = ft.TextField(label="Resolución", value=f[3], width=ancho)
        mapa = {"nombre": n, "cantidad": c, "resolucion": r}

        def guardar(e):
            errores, (nv, cv, rv) = _validar_carrera(n.value, c.value, r.value, id_actual=f[0])
            for clave, campo in mapa.items():
                poner_error(campo, errores.get(clave))
            if errores:
                page.update()
                return
            ok, _ = _ejecutar("UPDATE carrera SET nom_carrera = ?, cant_materias = ?, resolucion = ? "
                              "WHERE id_carrera = ?", (nv, cv, rv, f[0]))
            cerrar_dialogo(page, dialogo)
            if ok:
                refrescar_todo()
                avisar(page, "Carrera modificada correctamente.")
            else:
                avisar(page, "No se pudo modificar la carrera.")

        dialogo = None
        dialogo = ft.AlertDialog(
            modal=True, title=ft.Text("Modificar carrera"),
            content=ft.Column([n, c, r], tight=True, spacing=12, width=ancho + 20),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: cerrar_dialogo(page, dialogo)),
                     ft.Button(content=ft.Text("Guardar"), on_click=guardar)],
        )
        page.show_dialog(dialogo)

    def eliminar(f):
        if f[4] > 0:
            return mostrar_mensaje(
                page, "No se puede eliminar",
                f"La carrera «{f[1]}» tiene {f[4]} materia(s) cargada(s). "
                "Eliminá primero esas materias.")

        def borrar():
            ok, _ = _ejecutar("DELETE FROM carrera WHERE id_carrera = ?", (f[0],))
            if ok:
                refrescar_todo()
                avisar(page, "Carrera eliminada.")
            else:
                avisar(page, "No se pudo eliminar la carrera.")

        confirmar(page, "Eliminar carrera", f"¿Eliminar la carrera «{f[1]}»?", borrar,
                  texto_boton="Eliminar")

    registrar(cargar)
    cargar()
    return _columna([
        tarjeta_formulario(
            "Nueva carrera", ft.Icons.SCHOOL, COLOR_CARRERAS,
            [nombre, cantidad, resolucion,
             ft.Button(content=ft.Text("Agregar carrera"), icon=ft.Icons.ADD, on_click=agregar)],
            ayuda="Completá los datos del plan de estudios y tocá «Agregar carrera»."),
        _lista("Carreras cargadas", ft.Icons.LIST_ALT, COLOR_CARRERAS,
               [_tabla_centrada(tabla), vacio]),
    ])


# =====================================================================
#  MATERIAS
# =====================================================================

def _opciones_carreras():
    return [(f[0], f[1]) for f in _consultar("SELECT id_carrera, nom_carrera FROM carrera ORDER BY nom_carrera")]


def _validar_materia(id_carrera, codigo, nombre, horas, id_actual=0):
    errores = {}
    nombre = " ".join((nombre or "").split())
    cod = _numero_positivo(codigo)
    hs = _numero_positivo(horas)
    if not id_carrera:
        errores["carrera"] = "Elegí la carrera."
    if cod is None:
        errores["codigo"] = "Ingresá un número mayor a 0."
    elif id_carrera and _consultar(
            "SELECT 1 FROM materia WHERE id_carrera = ? AND materia_id = ? AND id_materia != ?",
            (int(id_carrera), cod, id_actual)):
        errores["codigo"] = "Ya existe una materia con ese código en la carrera."
    if not nombre:
        errores["nombre"] = "Ingresá el nombre de la materia."
    if hs is None:
        errores["horas"] = "Ingresá un número mayor a 0."
    return errores, (int(id_carrera) if id_carrera else None, cod, nombre, hs)


def _tab_materias(page, refrescar_todo, registrar):
    carrera = desplegable("Carrera", [], ancho=380)
    codigo = campo("Código de la materia", ft.Icons.TAG, 210, max_length=5,
                   input_filter=solo_numeros(), keyboard_type=ft.KeyboardType.NUMBER)
    nombre = campo("Nombre de la materia", ft.Icons.BOOK, 380)
    horas = campo("Horas", ft.Icons.SCHEDULE, 140, max_length=3,
                  input_filter=solo_numeros(), keyboard_type=ft.KeyboardType.NUMBER)
    campos = {"carrera": carrera, "codigo": codigo, "nombre": nombre, "horas": horas}
    autolimpiar(codigo, nombre, horas)
    aviso_sin_carreras = ft.Text("Primero cargá al menos una carrera en la pestaña «Carreras».",
                                 color=ft.Colors.ORANGE_800, visible=False)

    buscador = campo("Buscar por materia, código o carrera", ft.Icons.SEARCH, 420,
                     on_change=lambda e: cargar_tabla())
    tabla = ft.DataTable(columns=[
        ft.DataColumn(label=ft.Text("Carrera")),
        ft.DataColumn(label=ft.Text("Código")),
        ft.DataColumn(label=ft.Text("Materia")),
        ft.DataColumn(label=ft.Text("Horas")),
        ft.DataColumn(label=ft.Text("Acciones")),
    ], rows=[])
    vacio = ft.Text("No hay materias para mostrar.", color=ft.Colors.GREY_600)

    def cargar_opciones():
        opciones = _opciones_carreras()
        ids = {str(o[0]) for o in opciones}
        actual = carrera.value if carrera.value in ids else None
        actualizar_opciones(carrera, opciones, actual)
        aviso_sin_carreras.visible = not opciones

    def cargar_tabla():
        patron = f"%{(buscador.value or '').strip()}%"
        filas = _consultar(
            "SELECT m.id_materia, m.materia_id, m.nom_materia, m.cant_horas, m.id_carrera, "
            "c.nom_carrera, (SELECT COUNT(*) FROM designacion d WHERE d.id_materia = m.id_materia) "
            "FROM materia m JOIN carrera c ON c.id_carrera = m.id_carrera "
            "WHERE m.nom_materia LIKE ? OR c.nom_carrera LIKE ? OR CAST(m.materia_id AS TEXT) LIKE ? "
            "ORDER BY c.nom_carrera, m.materia_id", (patron, patron, patron))
        tabla.rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(f[5])),
                ft.DataCell(ft.Text(str(f[1]))),
                ft.DataCell(ft.Text(f[2])),
                ft.DataCell(ft.Text(str(f[3]))),
                ft.DataCell(ft.Row(spacing=0, controls=[
                    ft.IconButton(icon=ft.Icons.EDIT, tooltip="Modificar",
                                  on_click=lambda e, fila=f: editar(fila)),
                    ft.IconButton(icon=ft.Icons.DELETE, tooltip="Eliminar",
                                  on_click=lambda e, fila=f: eliminar(fila)),
                ])),
            ]) for f in filas
        ]
        tabla.visible = bool(filas)
        vacio.visible = not filas

    def recargar():
        cargar_opciones()
        cargar_tabla()
        page.update()

    def agregar(e):
        errores, (id_c, cod, n, hs) = _validar_materia(carrera.value, codigo.value, nombre.value, horas.value)
        for clave, campo in campos.items():
            poner_error(campo, errores.get(clave))
        if errores:
            page.update()
            return
        ok, _ = _ejecutar("INSERT INTO materia (materia_id, nom_materia, cant_horas, id_carrera) "
                          "VALUES (?, ?, ?, ?)", (cod, n, hs, id_c))
        if not ok:
            return avisar(page, "No se pudo guardar la materia.")
        for campo in (codigo, nombre, horas):   # la carrera queda elegida para cargar la siguiente
            campo.value = ""
        refrescar_todo()
        avisar(page, f"Materia «{n}» guardada correctamente.")

    def editar(f):
        ancho = 400
        c_dd = desplegable("Carrera", _opciones_carreras(), valor=f[4], ancho=ancho)
        cod = ft.TextField(label="Código de la materia", value=str(f[1]), width=ancho, max_length=5,
                           input_filter=solo_numeros())
        n = ft.TextField(label="Nombre de la materia", value=f[2], width=ancho)
        hs = ft.TextField(label="Horas", value=str(f[3]), width=ancho, max_length=3,
                          input_filter=solo_numeros())
        mapa = {"carrera": c_dd, "codigo": cod, "nombre": n, "horas": hs}

        def guardar(e):
            errores, (id_c, cv, nv, hv) = _validar_materia(c_dd.value, cod.value, n.value, hs.value,
                                                           id_actual=f[0])
            for clave, campo in mapa.items():
                poner_error(campo, errores.get(clave))
            if errores:
                page.update()
                return
            ok, _ = _ejecutar("UPDATE materia SET materia_id = ?, nom_materia = ?, cant_horas = ?, "
                              "id_carrera = ? WHERE id_materia = ?", (cv, nv, hv, id_c, f[0]))
            cerrar_dialogo(page, dialogo)
            if ok:
                refrescar_todo()
                avisar(page, "Materia modificada correctamente.")
            else:
                avisar(page, "No se pudo modificar la materia.")

        dialogo = None
        dialogo = ft.AlertDialog(
            modal=True, title=ft.Text("Modificar materia"),
            content=ft.Column([c_dd, cod, n, hs], tight=True, spacing=12, width=ancho + 20),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: cerrar_dialogo(page, dialogo)),
                     ft.Button(content=ft.Text("Guardar"), on_click=guardar)],
        )
        page.show_dialog(dialogo)

    def eliminar(f):
        if f[6] > 0:
            return mostrar_mensaje(
                page, "No se puede eliminar",
                f"La materia «{f[2]}» tiene {f[6]} designación(es) registrada(s). "
                "Eliminá primero esas designaciones.")

        def borrar():
            ok, _ = _ejecutar("DELETE FROM materia WHERE id_materia = ?", (f[0],))
            if ok:
                refrescar_todo()
                avisar(page, "Materia eliminada.")
            else:
                avisar(page, "No se pudo eliminar la materia.")

        confirmar(page, "Eliminar materia", f"¿Eliminar la materia «{f[2]}»?", borrar,
                  texto_boton="Eliminar")

    registrar(recargar)
    cargar_opciones()
    cargar_tabla()
    return _columna([
        aviso_sin_carreras,
        tarjeta_formulario(
            "Nueva materia", ft.Icons.BOOK, COLOR_MATERIAS,
            [carrera, codigo, nombre, horas,
             ft.Button(content=ft.Text("Agregar materia"), icon=ft.Icons.ADD, on_click=agregar)],
            ayuda="Elegí la carrera y completá los datos de la materia."),
        _lista("Materias cargadas", ft.Icons.LIST_ALT, COLOR_MATERIAS,
               [buscador, _tabla_centrada(tabla), vacio]),
    ])


# =====================================================================
#  DESIGNACIONES
# =====================================================================

def _opciones_codigo(lista):
    """[("V", "Vespertino")] -> [("V", "V - Vespertino")] para los desplegables."""
    return [(codigo, f"{codigo} - {texto}") for codigo, texto in lista]


def _tab_designaciones(page, refrescar_todo, registrar):
    hoy = date.today()
    limites = dict(primera=date(hoy.year - 40, 1, 1), ultima=date(hoy.year + 3, 12, 31), inicial=hoy)

    docente = desplegable("Docente", [], ancho=420)
    materia = desplegable("Materia", [], ancho=420)
    fila_alta, alta = campo_fecha(page, "Fecha de alta", valor=hoy.strftime(FORMATO_FECHA),
                                  ancho=250, **limites)
    disposicion = campo("N° de disposición (S.D.N°)", ft.Icons.DESCRIPTION, 250)
    turno = desplegable("Turno", _opciones_codigo(TURNOS), valor="V", ancho=200)
    situacion = desplegable("Situación", _opciones_codigo(SITUACIONES), valor="I", ancho=200)
    anio = desplegable("Año", ANIOS, ancho=120)
    division = campo("División (ej: 1A)", None, 160)
    condicion = desplegable("Condición", _opciones_codigo(CONDICIONES), ancho=220)
    tipo_designacion = desplegable("Tipo de alta", TIPOS_DESIGNACION,
                                   valor=TIPOS_DESIGNACION[0], ancho=250)
    campos = {"docente": docente, "materia": materia, "alta": alta, "disposicion": disposicion,
              "turno": turno, "situacion": situacion, "anio": anio, "division": division,
              "condicion": condicion, "tipo_designacion": tipo_designacion}
    autolimpiar(disposicion, division)
    aviso_faltan = ft.Text("", color=ft.Colors.ORANGE_800, visible=False)

    buscador = campo("Buscar por docente, DNI, materia o carrera", ft.Icons.SEARCH, 420,
                     on_change=lambda e: cargar_tabla())
    solo_vigentes = ft.Switch(label="Solo vigentes", value=False, on_change=lambda e: cargar_tabla())
    # Una barra desplegable por docente; al tocarla se ven sus designaciones.
    listado = ft.Column(spacing=8)
    vacio = ft.Text("No hay designaciones para mostrar.", color=ft.Colors.GREY_600)

    def cargar_opciones():
        docentes = [(f[0], f"{f[1]}, {f[2]} - DNI {f[3]}") for f in _consultar(
            "SELECT id_docente, apellido, nombre, dni FROM docentes WHERE activo = 1 "
            "ORDER BY apellido, nombre")]
        materias = [(f[0], f"{f[1]} - {f[2]}") for f in _consultar(
            "SELECT m.id_materia, c.nom_carrera, m.nom_materia FROM materia m "
            "JOIN carrera c ON c.id_carrera = m.id_carrera ORDER BY c.nom_carrera, m.nom_materia")]
        for dd, opciones in ((docente, docentes), (materia, materias)):
            ids = {str(o[0]) for o in opciones}
            actualizar_opciones(dd, opciones, dd.value if dd.value in ids else None)
        faltan = []
        if not docentes:
            faltan.append("docentes activos")
        if not materias:
            faltan.append("materias")
        aviso_faltan.value = ("Para designar necesitás cargar antes: " + " y ".join(faltan) + ".") if faltan else ""
        aviso_faltan.visible = bool(faltan)

    def cargar_tabla():
        patron = f"%{(buscador.value or '').strip()}%"
        filas = _consultar(
            "SELECT de.id_docente_materia, doc.apellido, doc.nombre, doc.dni, m.nom_materia, "
            "c.nom_carrera, de.fecha_alta, de.fecha_baja, de.motivo_baja, de.nro_disposicion, "
            "de.turno, de.situacion, de.anio, de.division, de.condicion, de.tipo_designacion "
            "FROM designacion de "
            "JOIN docentes doc ON doc.id_docente = de.id_docente "
            "JOIN materia m ON m.id_materia = de.id_materia "
            "JOIN carrera c ON c.id_carrera = m.id_carrera "
            "WHERE doc.apellido LIKE ? OR doc.nombre LIKE ? OR CAST(doc.dni AS TEXT) LIKE ? "
            "OR m.nom_materia LIKE ? OR c.nom_carrera LIKE ? "
            "ORDER BY doc.apellido, doc.nombre, c.nom_carrera, m.nom_materia", (patron,) * 5)
        if solo_vigentes.value:
            filas = [f for f in filas if es_vigente(f[7])]

        grupos = {}
        for f in filas:
            grupos.setdefault((f[1], f[2], f[3]), []).append(f)

        def fila_designacion(f):
            vigente = es_vigente(f[7])
            detalle = f"{f[5]}  ·  Disposición {f[9]}  ·  Alta {f[6]}"
            if f[7]:
                detalle += f"  ·  Baja {f[7]}"
            extra = [f"Turno {f[10]}" if f[10] else "", f[11] or "",
                     f"{f[12] or ''} {f[13] or ''}".strip(), f[14] or "", f[15] or ""]
            extra = "  ·  ".join(x for x in extra if x)
            detalle += f"\n{extra}" if extra else "\nFaltan datos para la constancia (turno, año, etc.)"
            return ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Column(expand=True, spacing=2, controls=[
                            ft.Text(f[4], weight=ft.FontWeight.BOLD),
                            ft.Text(detalle, size=12, color=ft.Colors.GREY_700),
                        ]),
                        ft.Text(estado_designacion(f[7]), size=12, weight=ft.FontWeight.W_500,
                                color=ft.Colors.GREEN_700 if vigente else ft.Colors.GREY_600),
                        ft.IconButton(icon=ft.Icons.EDIT, tooltip="Modificar / dar de baja",
                                      on_click=lambda e, fila=f: editar(fila)),
                        ft.IconButton(icon=ft.Icons.DELETE, tooltip="Eliminar",
                                      on_click=lambda e, fila=f: eliminar(fila)),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding.symmetric(horizontal=16, vertical=6),
            )

        barras = []
        for (apellido, nombre_d, dni_d), items in grupos.items():
            vigentes = sum(1 for i in items if es_vigente(i[7]))
            barras.append(ft.ExpansionTile(
                leading=ft.Icon(ft.Icons.PERSON, color=COLOR_DESIGNACIONES),
                title=ft.Text(f"{apellido}, {nombre_d}", weight=ft.FontWeight.BOLD),
                subtitle=ft.Text(f"DNI {dni_d}  ·  {len(items)} designación(es), {vigentes} vigente(s)"),
                controls=[fila_designacion(i) for i in items],
            ))
        listado.controls = barras
        listado.visible = bool(filas)
        vacio.visible = not filas

    def recargar():
        cargar_opciones()
        cargar_tabla()
        page.update()

    def agregar(e):
        errores = {}
        if not docente.value:
            errores["docente"] = "Elegí el docente."
        if not materia.value:
            errores["materia"] = "Elegí la materia."
        fecha_alta = parse_fecha(alta.value)
        if fecha_alta is None:
            errores["alta"] = "Elegí la fecha con el calendario."
        if not disposicion.value.strip():
            errores["disposicion"] = "Ingresá el número de disposición."
        for clave in ("turno", "situacion", "anio", "condicion", "tipo_designacion"):
            if not campos[clave].value:
                errores[clave] = "Elegí una opción."
        if not (division.value or "").strip():
            errores["division"] = "Ingresá la división."
        if not errores:
            previas = _consultar("SELECT fecha_baja FROM designacion WHERE id_docente = ? AND id_materia = ?",
                                 (int(docente.value), int(materia.value)))
            if any(es_vigente(p[0]) for p in previas):
                errores["materia"] = "El docente ya tiene una designación vigente en esa materia."
        for clave, campo in campos.items():
            poner_error(campo, errores.get(clave))
        if errores:
            page.update()
            return

        ok, _ = _ejecutar(
            "INSERT INTO designacion (id_docente, id_materia, fecha_alta, estado, nro_disposicion, "
            "turno, situacion, anio, division, condicion, tipo_designacion) "
            "VALUES (?, ?, ?, 'Vigente', ?, ?, ?, ?, ?, ?, ?)",
            (int(docente.value), int(materia.value), fecha_alta.strftime(FORMATO_FECHA),
             disposicion.value.strip(), turno.value, situacion.value, anio.value,
             division.value.strip().upper(), condicion.value, tipo_designacion.value))
        if not ok:
            return avisar(page, "No se pudo guardar la designación.")
        docente.value = None
        materia.value = None
        disposicion.value = ""
        division.value = ""
        anio.value = None
        condicion.value = None
        refrescar_todo()
        avisar(page, "Designación registrada correctamente.")

    def editar(f):
        ancho = 420
        fila_a, a = campo_fecha(page, "Fecha de alta", valor=f[6], ancho=ancho, **limites)
        disp = ft.TextField(label="N° de disposición (S.D.N°)", value=str(f[9]), width=ancho)
        medio = ancho // 2 - 6
        tur = desplegable("Turno", _opciones_codigo(TURNOS), valor=f[10], ancho=medio)
        sit = desplegable("Situación", _opciones_codigo(SITUACIONES), valor=f[11], ancho=medio)
        an = desplegable("Año", ANIOS, valor=f[12], ancho=medio)
        div = ft.TextField(label="División (ej: 1A)", value=f[13] or "", width=medio)
        cond = desplegable("Condición", _opciones_codigo(CONDICIONES), valor=f[14], ancho=medio)
        tipo = desplegable("Tipo de alta", TIPOS_DESIGNACION, valor=f[15], ancho=medio)
        fila_b, b = campo_fecha(page, "Fecha de baja (vacía = sigue vigente)", valor=f[7] or "",
                                ancho=ancho, permitir_borrar=True, **limites)
        motivo = ft.TextField(label="Motivo de la baja (ej: Designación a término)",
                              value=f[8] or "", width=ancho)
        error = ft.Text(color=ft.Colors.RED_700, visible=False)
        ocultar_error_al_escribir(page, error, disp, motivo, div)

        def guardar(e):
            def fallo(mensaje):
                error.value = mensaje
                error.visible = True
                page.update()

            fecha_a = parse_fecha(a.value)
            if fecha_a is None:
                return fallo("Elegí la fecha de alta con el calendario.")
            if not disp.value.strip():
                return fallo("Ingresá el número de disposición.")
            baja = (b.value or "").strip()
            if baja:
                fecha_b = parse_fecha(baja)
                if fecha_b is None:
                    return fallo("Elegí la fecha de baja con el calendario.")
                if fecha_b < fecha_a:
                    return fallo("La baja no puede ser anterior al alta.")
                if not motivo.value.strip():
                    motivo.value = tipo.value or TIPOS_DESIGNACION[0]
            estado = "Vigente" if es_vigente(baja or None) else "Baja"
            ok, _ = _ejecutar(
                "UPDATE designacion SET fecha_alta = ?, nro_disposicion = ?, fecha_baja = ?, "
                "motivo_baja = ?, estado = ?, turno = ?, situacion = ?, anio = ?, division = ?, "
                "condicion = ?, tipo_designacion = ? WHERE id_docente_materia = ?",
                (fecha_a.strftime(FORMATO_FECHA), disp.value.strip(), baja or None,
                 motivo.value.strip() if baja else None, estado, tur.value, sit.value, an.value,
                 (div.value or "").strip().upper(), cond.value, tipo.value, f[0]))
            cerrar_dialogo(page, dialogo)
            if ok:
                refrescar_todo()
                avisar(page, "Designación modificada correctamente.")
            else:
                avisar(page, "No se pudo modificar la designación.")

        dialogo = None
        dialogo = ft.AlertDialog(
            modal=True, title=ft.Text("Modificar designación"),
            content=ft.Column(
                [ft.Text(f"{f[1]}, {f[2]}", weight=ft.FontWeight.BOLD),
                 ft.Text(f"{f[4]} ({f[5]})"),
                 fila_a, disp,
                 ft.Row(controls=[tur, sit], spacing=12), ft.Row(controls=[an, div], spacing=12),
                 ft.Row(controls=[cond, tipo], spacing=12),
                 fila_b, motivo, error],
                tight=True, spacing=12, width=ancho + 20, scroll=ft.ScrollMode.AUTO),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: cerrar_dialogo(page, dialogo)),
                     ft.Button(content=ft.Text("Guardar"), on_click=guardar)],
        )
        page.show_dialog(dialogo)

    def eliminar(f):
        cubiertas = _consultar("SELECT COUNT(*) FROM suplencia WHERE id_designacion_titular = ?",
                               (f[0],))
        if cubiertas and cubiertas[0][0]:
            mostrar_mensaje(page, "No se puede eliminar",
                            f"La designación de {f[1]}, {f[2]} en «{f[4]}» tiene suplencias "
                            "registradas. Eliminalas primero desde la pestaña «Suplencias».")
            return

        def borrar():
            ok, _ = _ejecutar("DELETE FROM designacion WHERE id_docente_materia = ?", (f[0],))
            if ok:
                refrescar_todo()
                avisar(page, "Designación eliminada.")
            else:
                avisar(page, "No se pudo eliminar la designación.")

        confirmar(
            page, "Eliminar designación",
            f"¿Eliminar la designación de {f[1]}, {f[2]} en «{f[4]}»? Si el docente dejó de "
            "dictar la materia, conviene registrar la baja (botón de modificar) para no perder "
            "el historial.",
            borrar, texto_boton="Eliminar")

    registrar(recargar)
    cargar_opciones()
    cargar_tabla()
    return _columna([
        aviso_faltan,
        tarjeta_formulario(
            "Nueva designación", ft.Icons.ASSIGNMENT_IND, COLOR_DESIGNACIONES,
            [docente, materia, fila_alta, disposicion,
             turno, situacion, anio, division, condicion, tipo_designacion,
             ft.Button(content=ft.Text("Registrar designación"), icon=ft.Icons.ADD, on_click=agregar)],
            ayuda="Elegí el docente y la materia, la fecha de alta (toma de posesión), la disposición "
                  "y los datos que salen en la constancia de trabajo (turno, situación, año, "
                  "división y condición)."),
        _lista("Designaciones por docente", ft.Icons.ACCOUNT_TREE, COLOR_DESIGNACIONES,
               [ft.Row(controls=[buscador, solo_vigentes], wrap=True, spacing=14), listado, vacio]),
    ])


# =====================================================================
#  PANTALLA
# =====================================================================

def vista_academica(page: ft.Page):
    recargas = []

    def refrescar_todo():
        for recargar in recargas:
            recargar()

    registrar = recargas.append
    carreras = _tab_carreras(page, refrescar_todo, registrar)
    materias = _tab_materias(page, refrescar_todo, registrar)
    designaciones = _tab_designaciones(page, refrescar_todo, registrar)
    from crud.reportes import tab_reportes
    from crud.suplencias import tab_suplencias
    suplencias = tab_suplencias(page, refrescar_todo, registrar)
    reportes = tab_reportes(page, refrescar_todo, registrar)

    return ft.Tabs(
        length=5,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(
                    tab_alignment=ft.TabAlignment.CENTER,
                    tabs=[ft.Tab(label="Carreras"), ft.Tab(label="Materias"),
                          ft.Tab(label="Designaciones"), ft.Tab(label="Suplencias"),
                          ft.Tab(label="Reportes")],
                ),
                ft.TabBarView(expand=True, controls=[carreras, materias, designaciones,
                                                     suplencias, reportes]),
            ],
        ),
    )
