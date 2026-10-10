"""Buscar docente: ficha completa con datos personales, materias y carreras,
licencias y carpeta médica (certificados médicos)."""
import sqlite3
from datetime import date, timedelta

import flet as ft

from config import TIPOS_LICENCIA
from database.conexion import conectar
from database.consultas import (
    FORMATO_FECHA, certificados_de, designaciones_detalle, licencias_de, listar_docentes,
    parse_fecha,
)
from ui import (
    avisar, campo_fecha, cerrar_dialogo, confirmar, desplegable, ocultar_error_al_escribir,
)

COLOR = ft.Colors.INDIGO_700


# ---------- CÁLCULOS ----------

def _edad(nacimiento, hoy):
    fecha = parse_fecha(nacimiento)
    if fecha is None:
        return None
    return hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))


def _reposos(certificados):
    """[(certificado, desde, hasta)] calculando el último día de cada reposo."""
    resultado = []
    for c in certificados:
        desde = parse_fecha(c[2])
        hasta = desde + timedelta(days=c[3] - 1) if desde else None
        resultado.append((c, desde, hasta))
    return resultado


def _situacion(certificados, licencias, hoy):
    """Lista de textos con lo que tiene vigente HOY (carpeta médica o licencias)."""
    vigentes = []
    for c, desde, hasta in _reposos(certificados):
        if desde and desde <= hoy <= hasta:
            vigentes.append(f"Carpeta médica hasta el {hasta.strftime(FORMATO_FECHA)} "
                            f"({c[3]} día(s), {c[4]})")
    for _id, tipo, desde, hasta, _obs in licencias:
        d1, d2 = parse_fecha(desde), parse_fecha(hasta)
        if d1 and d2 and d1 <= hoy <= d2:
            vigentes.append(f"Licencia: {tipo} hasta el {hasta}")
    return vigentes


# ---------- PIEZAS VISUALES ----------

def _etiqueta(texto, color):
    return ft.Container(
        content=ft.Text(texto, size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.W_600),
        bgcolor=color, border_radius=20,
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
    )


def _dato(etiqueta, valor, icono):
    return ft.Container(
        width=270,
        content=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Icon(icono, size=20, color=COLOR),
                ft.Column(spacing=0, expand=True, controls=[
                    ft.Text(etiqueta, size=12, color=ft.Colors.GREY_600),
                    ft.Text(str(valor) if valor not in (None, "") else "-", size=14,
                            weight=ft.FontWeight.W_500, selectable=True),
                ]),
            ],
        ),
    )


def _seccion(titulo, icono, color, contenido, accion=None):
    cabecera = [ft.Icon(icono, color=color, size=24),
                ft.Text(titulo, size=17, weight=ft.FontWeight.BOLD, expand=True)]
    if accion is not None:
        cabecera.append(accion)
    return ft.Container(
        padding=18,
        border_radius=12,
        border=ft.Border.all(1, ft.Colors.GREY_300),
        content=ft.Column(spacing=12, controls=[ft.Row(controls=cabecera, spacing=10)] + contenido),
    )


def _vacio(texto):
    return ft.Text(texto, color=ft.Colors.GREY_600, italic=True)


def _tabla(columnas, filas):
    return ft.Row(scroll=ft.ScrollMode.AUTO, controls=[ft.DataTable(
        columns=[ft.DataColumn(label=ft.Text(c, weight=ft.FontWeight.BOLD)) for c in columnas],
        rows=filas,
        column_spacing=28,
        heading_row_height=42,
        data_row_min_height=42,
    )])


def _estado(texto, color):
    return ft.DataCell(ft.Text(texto, color=color, weight=ft.FontWeight.W_600))


# ---------- PANTALLA ----------

def vista_buscar_docente(page: ft.Page):
    seleccionado = {"dni": None}

    resultados = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
    contador = ft.Text(size=12, color=ft.Colors.GREY_600)
    ficha = ft.Column(spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)

    buscador = ft.TextField(
        label="DNI, nombre o apellido",
        prefix_icon=ft.Icons.SEARCH,
        border_radius=10,
        filled=True,
        on_change=lambda e: cargar_resultados(),
    )
    ver_inactivos = ft.Switch(label="Incluir inactivos", value=True,
                              on_change=lambda e: cargar_resultados())

    def mensaje_inicial():
        ficha.controls = [ft.Container(
            expand=True,
            padding=40,
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
                controls=[
                    ft.Icon(ft.Icons.PERSON_SEARCH, size=80, color=ft.Colors.GREY_400),
                    ft.Text("Buscá un docente y tocá su nombre", size=18,
                            color=ft.Colors.GREY_700),
                    ft.Text("Vas a ver sus datos, materias, carreras, licencias y carpeta médica.",
                            size=13, color=ft.Colors.GREY_600),
                ],
            ),
        )]

    # ---------- LISTA DE RESULTADOS ----------
    def cargar_resultados():
        docentes = listar_docentes(buscador.value or "",
                                   incluir_inactivos=bool(ver_inactivos.value))
        items = []
        for d in docentes:
            activo = bool(d[8])
            items.append(ft.ListTile(
                leading=ft.Icon(ft.Icons.PERSON if activo else ft.Icons.PERSON_OFF,
                                color=COLOR if activo else ft.Colors.GREY_500),
                title=ft.Text(f"{d[2]}, {d[1]}", weight=ft.FontWeight.W_500,
                              color=None if activo else ft.Colors.GREY_600),
                subtitle=ft.Text(f"DNI {d[0]}" + ("" if activo else " · inactivo"), size=12),
                selected=d[0] == seleccionado["dni"],
                dense=True,
                on_click=lambda e, doc=d: mostrar_ficha(doc),
            ))
        if not items:
            items.append(ft.Container(padding=10, content=_vacio("No se encontraron docentes.")))
        resultados.controls = items
        contador.value = f"{len(docentes)} resultado(s)"
        page.update()

    # ---------- FICHA ----------
    def mostrar_ficha(d):
        seleccionado["dni"] = d[0]
        hoy = date.today()
        designaciones = designaciones_detalle(d[0])
        certificados = certificados_de(d[0])
        licencias = licencias_de(d[0])

        # --- Encabezado ---
        activo = bool(d[8])
        situacion = _situacion(certificados, licencias, hoy)
        etiquetas = [_etiqueta("Activo" if activo else "Inactivo",
                               ft.Colors.GREEN_700 if activo else ft.Colors.GREY_600),
                     _etiqueta(str(d[7]), COLOR)]
        if situacion:
            etiquetas.append(_etiqueta("Con licencia / carpeta médica", ft.Colors.RED_700))
        elif activo:
            etiquetas.append(_etiqueta("Prestando servicio", ft.Colors.TEAL_700))

        cabecera = ft.Container(
            padding=20,
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.06, COLOR),
            content=ft.Row(spacing=18, controls=[
                ft.CircleAvatar(
                    content=ft.Text(f"{str(d[2])[:1]}{str(d[1])[:1]}".upper(), size=22,
                                    weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    bgcolor=COLOR, radius=34),
                ft.Column(spacing=6, expand=True, controls=[
                    ft.Text(f"{d[2]}, {d[1]}", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(f"DNI {d[0]} · CUIL {d[3]}", size=14, color=ft.Colors.GREY_700),
                    ft.Row(controls=etiquetas, spacing=8, wrap=True),
                ]),
            ]),
        )

        controles = [cabecera]

        if situacion:
            controles.append(ft.Container(
                padding=ft.Padding.symmetric(horizontal=18, vertical=12),
                border_radius=10,
                bgcolor=ft.Colors.RED_50,
                content=ft.Column(spacing=4, controls=[
                    ft.Row(spacing=8, controls=[
                        ft.Icon(ft.Icons.WARNING_AMBER, color=ft.Colors.RED_700),
                        ft.Text("Situación actual", weight=ft.FontWeight.BOLD,
                                color=ft.Colors.RED_800)]),
                ] + [ft.Text(f"• {s}", size=13) for s in situacion]),
            ))

        # --- Datos personales ---
        edad = _edad(d[4], hoy)
        nacimiento = f"{d[4]} ({edad} años)" if edad is not None else d[4]
        controles.append(_seccion("Datos personales", ft.Icons.BADGE, COLOR, [
            ft.Row(wrap=True, spacing=16, run_spacing=14, controls=[
                _dato("Fecha de nacimiento", nacimiento, ft.Icons.CAKE),
                _dato("Domicilio", d[5], ft.Icons.HOME),
                _dato("Email", d[6], ft.Icons.EMAIL),
                _dato("Carácter", d[7], ft.Icons.WORK_OUTLINE),
            ]),
        ]))

        # --- Materias y carreras ---
        vigentes = [x for x in designaciones if x[7]]
        carreras = sorted({x[1] for x in vigentes})
        horas = sum(int(x[2] or 0) for x in vigentes)
        contenido = []
        if designaciones:
            contenido.append(ft.Row(wrap=True, spacing=16, run_spacing=10, controls=[
                _dato("Materias vigentes", len(vigentes), ft.Icons.MENU_BOOK),
                _dato("Horas cátedra vigentes", horas, ft.Icons.SCHEDULE),
                _dato("Carrera(s)", ", ".join(carreras) or "-", ft.Icons.SCHOOL),
            ]))
            filas = []
            for mat, car, hs, alta, baja, disp, motivo, vigente in designaciones:
                if vigente:
                    estado = _estado("Vigente" if not baja else f"Vigente hasta {baja}",
                                     ft.Colors.GREEN_700)
                else:
                    estado = _estado("Baja" + (f" ({motivo})" if motivo else ""),
                                     ft.Colors.GREY_600)
                filas.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(mat))), ft.DataCell(ft.Text(str(car))),
                    ft.DataCell(ft.Text(str(hs))), ft.DataCell(ft.Text(str(alta))),
                    ft.DataCell(ft.Text(str(baja or "-"))), ft.DataCell(ft.Text(str(disp))),
                    estado,
                ]))
            contenido.append(_tabla(
                ["Materia", "Carrera", "Horas", "Alta", "Baja", "Disposición", "Estado"], filas))
        else:
            contenido.append(_vacio("No tiene materias asignadas."))
        controles.append(_seccion(f"Materias y carreras ({len(designaciones)})",
                                  ft.Icons.MENU_BOOK, ft.Colors.PURPLE_700, contenido))

        # --- Licencias ---
        if licencias:
            filas = []
            for lic in licencias:
                lid, tipo, desde, hasta, obs = lic
                d1, d2 = parse_fecha(desde), parse_fecha(hasta)
                if d1 and d2 and d1 <= hoy <= d2:
                    estado = _estado("En curso", ft.Colors.RED_700)
                elif d1 and d1 > hoy:
                    estado = _estado("Programada", ft.Colors.ORANGE_800)
                else:
                    estado = _estado("Finalizada", ft.Colors.GREY_600)
                dias = (d2 - d1).days + 1 if d1 and d2 else "-"
                filas.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(tipo))), ft.DataCell(ft.Text(str(desde))),
                    ft.DataCell(ft.Text(str(hasta))), ft.DataCell(ft.Text(str(dias))),
                    ft.DataCell(ft.Text(str(obs or "-"))), estado,
                    ft.DataCell(ft.IconButton(
                        icon=ft.Icons.DELETE, tooltip="Eliminar licencia",
                        on_click=lambda e, l=lic: borrar_licencia(d, l))),
                ]))
            contenido = [_tabla(["Tipo", "Desde", "Hasta", "Días", "Observaciones",
                                 "Estado", ""], filas)]
        else:
            contenido = [_vacio("No tiene licencias registradas.")]
        controles.append(_seccion(
            f"Licencias ({len(licencias)})", ft.Icons.EVENT_BUSY, ft.Colors.ORANGE_800, contenido,
            accion=ft.Button(content=ft.Text("Registrar licencia"), icon=ft.Icons.ADD,
                             on_click=lambda e: abrir_licencia(d))))

        # --- Carpeta médica ---
        reposos = _reposos(certificados)
        if reposos:
            total = sum(c[3] for c, _d, _h in reposos if _d and _d.year == hoy.year)
            filas = []
            for c, desde, hasta in reposos:
                if desde and desde <= hoy <= hasta:
                    estado = _estado("Vigente", ft.Colors.RED_700)
                elif desde and desde > hoy:
                    estado = _estado("Programada", ft.Colors.ORANGE_800)
                else:
                    estado = _estado("Finalizada", ft.Colors.GREY_600)
                filas.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(c[2]))),
                    ft.DataCell(ft.Text(hasta.strftime(FORMATO_FECHA) if hasta else "-")),
                    ft.DataCell(ft.Text(str(c[3]))),
                    ft.DataCell(ft.Text(str(c[4]) + (f" (Mat. {c[5]})" if c[5] else ""))),
                    ft.DataCell(ft.Text(str(c[6] or "-"))),
                    estado,
                ]))
            contenido = [
                ft.Text(f"Días de reposo en {hoy.year}: {total}", size=13, color=ft.Colors.GREY_700),
                _tabla(["Desde", "Hasta", "Días", "Médico/a", "Observaciones", "Estado"], filas),
            ]
        else:
            contenido = [_vacio("No tiene certificados médicos registrados.")]
        controles.append(_seccion(f"Carpeta médica ({len(certificados)})",
                                  ft.Icons.MEDICAL_SERVICES, ft.Colors.RED_700, contenido))

        ficha.controls = controles
        cargar_resultados()  # marca al docente elegido en la lista

    # ---------- LICENCIAS: ALTA Y BAJA ----------
    def abrir_licencia(d):
        ancho = 420
        hoy = date.today()
        limites = dict(primera=date(hoy.year - 5, 1, 1), ultima=date(hoy.year + 2, 12, 31))
        tipo = desplegable("Tipo de licencia", TIPOS_LICENCIA, ancho=ancho)
        fila_desde, desde = campo_fecha(page, "Desde", valor=hoy.strftime(FORMATO_FECHA),
                                        ancho=ancho, inicial=hoy, **limites)
        fila_hasta, hasta = campo_fecha(page, "Hasta", valor=hoy.strftime(FORMATO_FECHA),
                                        ancho=ancho, inicial=hoy, **limites)
        observaciones = ft.TextField(label="Observaciones (opcional)", width=ancho,
                                     multiline=True, min_lines=2, max_lines=4)
        error = ft.Text(color=ft.Colors.RED_700, visible=False)
        ocultar_error_al_escribir(page, error, observaciones)

        def mostrar_error(mensaje):
            error.value = mensaje
            error.visible = True
            page.update()

        def guardar(e):
            d1, d2 = parse_fecha(desde.value), parse_fecha(hasta.value)
            if not tipo.value:
                return mostrar_error("Elegí el tipo de licencia.")
            if d1 is None or d2 is None:
                return mostrar_error("Elegí las fechas con el calendario.")
            if d2 < d1:
                return mostrar_error("La fecha 'Hasta' no puede ser anterior a 'Desde'.")

            conexion = conectar()
            try:
                with conexion:
                    fila = conexion.execute(
                        "SELECT id_docente FROM docentes WHERE dni = ?", (d[0],)).fetchone()
                    conexion.execute(
                        "INSERT INTO licencia (id_docente, tipo, fecha_desde, fecha_hasta, "
                        "observaciones) VALUES (?, ?, ?, ?, ?)",
                        (fila[0], tipo.value, desde.value, hasta.value,
                         (observaciones.value or "").strip()))
            except (sqlite3.Error, TypeError) as err:
                print("Error al guardar la licencia:", err)
                return mostrar_error("No se pudo guardar la licencia.")
            finally:
                conexion.close()

            cerrar_dialogo(page, dialogo)
            mostrar_ficha(d)
            avisar(page, "Licencia registrada.")

        dialogo = None
        dialogo = ft.AlertDialog(
            modal=True,
            title=ft.Text("Registrar licencia"),
            content=ft.Column(
                tight=True, width=ancho + 20, spacing=12,
                controls=[ft.Text(f"{d[2]}, {d[1]} - DNI {d[0]}", weight=ft.FontWeight.BOLD),
                          tipo, fila_desde, fila_hasta, observaciones, error],
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: cerrar_dialogo(page, dialogo)),
                ft.Button(content=ft.Text("Guardar"), icon=ft.Icons.SAVE, on_click=guardar),
            ],
        )
        page.show_dialog(dialogo)

    def borrar_licencia(d, lic):
        def borrar():
            conexion = conectar()
            try:
                with conexion:
                    conexion.execute("DELETE FROM licencia WHERE id_licencia = ?", (lic[0],))
            except sqlite3.Error as err:
                print("Error al eliminar la licencia:", err)
                avisar(page, "No se pudo eliminar la licencia.")
                return
            finally:
                conexion.close()
            mostrar_ficha(d)
            avisar(page, "Licencia eliminada.")

        confirmar(page, "Eliminar licencia",
                  f"¿Eliminar la licencia '{lic[1]}' del {lic[2]} al {lic[3]}?",
                  borrar, texto_boton="Eliminar")

    # ---------- ARMADO ----------
    mensaje_inicial()
    cargar_resultados()

    panel_busqueda = ft.Container(
        width=320,
        padding=16,
        border_radius=12,
        border=ft.Border.all(1, ft.Colors.GREY_300),
        content=ft.Column(
            expand=True, spacing=10,
            controls=[buscador, ft.Row(controls=[ver_inactivos, contador],
                                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                      ft.Divider(height=1), resultados],
        ),
    )

    encabezado = ft.Row(spacing=15, controls=[
        ft.Icon(ft.Icons.PERSON_SEARCH, size=36, color=COLOR),
        ft.Column(spacing=2, controls=[
            ft.Text("Buscar docente", size=28, weight=ft.FontWeight.BOLD),
            ft.Text("Toda la información del docente en un solo lugar.",
                    size=14, color=ft.Colors.GREY_600),
        ]),
    ])

    return ft.Column(
        data=cargar_resultados,  # la pestaña Registrar la usa para refrescar la lista
        expand=True, spacing=20,
        controls=[
            encabezado,
            ft.Row(expand=True, spacing=20, vertical_alignment=ft.CrossAxisAlignment.START,
                   controls=[panel_busqueda, ft.Container(expand=True, content=ficha)]),
        ],
    )
