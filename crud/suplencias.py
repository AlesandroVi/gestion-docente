"""Suplencias: qué suplente cubre la cátedra de qué docente, y desde/hasta cuándo.

La suplencia crea una designación normal para el suplente (situación "S", tipo "Suplencia"),
así aparece sola en su constancia de trabajo, en su ficha y en la planta docente."""
import sqlite3
from datetime import date

import flet as ft

from crud.academico import _columna, _consultar, _lista
from database.conexion import conectar
from database.consultas import FORMATO_FECHA, es_vigente, parse_fecha
from herramientas.avisos import ausentes_hoy
from ui import (
    actualizar_opciones, avisar, campo, campo_fecha, confirmar, desplegable, poner_error,
    tarjeta_formulario,
)

COLOR = ft.Colors.DEEP_ORANGE_700


def _al_elegir(lista, funcion):
    """Agrega `funcion` al evento de selección de un desplegable sin perder el original."""
    original = lista.on_select

    def manejador(e):
        original(e)
        funcion()

    lista.on_select = lista.on_change = manejador


def tab_suplencias(page, refrescar_todo, registrar):
    hoy = date.today()
    limites = dict(primera=date(hoy.year - 5, 1, 1), ultima=date(hoy.year + 3, 12, 31), inicial=hoy)

    titular = desplegable("Cátedra a cubrir (docente titular - materia)", [], ancho=520)
    suplente = desplegable("Docente suplente", [], ancho=420)
    fila_desde, desde = campo_fecha(page, "Desde", valor=hoy.strftime(FORMATO_FECHA),
                                    ancho=250, **limites)
    fila_hasta, hasta = campo_fecha(page, "Hasta", ancho=250, **limites)
    disposicion = campo("N° de disposición (S.D.N°)", ft.Icons.DESCRIPTION, 250)
    motivo = campo("Motivo (ej: licencia por maternidad)", ft.Icons.NOTES, 420)
    ayuda_ausencia = ft.Text("", size=12, color=ft.Colors.RED_700, visible=False)
    campos = {"titular": titular, "suplente": suplente, "desde": desde, "hasta": hasta,
              "disposicion": disposicion}

    listado = ft.Column(spacing=6)
    vacio = ft.Text("No hay suplencias registradas.", color=ft.Colors.GREY_600)
    solo_en_curso = ft.Switch(label="Solo en curso", value=True, on_change=lambda e: cargar_lista())
    designaciones = {}  # id designación titular -> datos

    # ---------- OPCIONES ----------
    def cargar_opciones():
        designaciones.clear()
        filas = _consultar(
            "SELECT de.id_docente_materia, de.id_docente, doc.apellido, doc.nombre, m.nom_materia, "
            "c.nom_carrera, de.fecha_baja "
            "FROM designacion de "
            "JOIN docentes doc ON doc.id_docente = de.id_docente "
            "JOIN materia m ON m.id_materia = de.id_materia "
            "JOIN carrera c ON c.id_carrera = m.id_carrera "
            "WHERE COALESCE(de.situacion, 'I') != 'S' "
            "ORDER BY doc.apellido, doc.nombre, m.nom_materia")
        ausentes = ausentes_hoy()
        opciones = []
        for f in filas:
            if not es_vigente(f[6]):
                continue
            designaciones[str(f[0])] = {"id_docente": f[1], "ausencia": ausentes.get(f[1])}
            marca = " (AUSENTE HOY)" if f[1] in ausentes else ""
            opciones.append((f[0], f"{f[2]}, {f[3]} - {f[4]} ({f[5]}){marca}"))
        actualizar_opciones(titular, opciones,
                            titular.value if titular.value in designaciones else None)

        docentes = [(f[0], f"{f[1]}, {f[2]} - DNI {f[3]}") for f in _consultar(
            "SELECT id_docente, apellido, nombre, dni FROM docentes WHERE activo = 1 "
            "ORDER BY apellido, nombre")]
        ids = {str(o[0]) for o in docentes}
        actualizar_opciones(suplente, docentes, suplente.value if suplente.value in ids else None)

    def al_elegir_titular():
        """Si el titular está de licencia, propone las fechas y el motivo."""
        dato = designaciones.get(titular.value or "")
        ausencia = dato and dato["ausencia"]
        if ausencia:
            ayuda_ausencia.value = (f"Este docente está ausente: {ausencia[0]} hasta el "
                                    f"{ausencia[1].strftime(FORMATO_FECHA)}. "
                                    "Se completó la fecha 'Hasta' con ese día.")
            hasta.value = ausencia[1].strftime(FORMATO_FECHA)
            if not (motivo.value or "").strip():
                motivo.value = ausencia[0]
        ayuda_ausencia.visible = bool(ausencia)
        page.update()

    _al_elegir(titular, al_elegir_titular)

    # ---------- LISTA ----------
    def cargar_lista():
        filas = _consultar(
            "SELECT s.id_suplencia, s.id_designacion_suplente, s.motivo, "
            "dt.apellido, dt.nombre, ds.apellido, ds.nombre, m.nom_materia, c.nom_carrera, "
            "sup.fecha_alta, sup.fecha_baja, sup.nro_disposicion "
            "FROM suplencia s "
            "JOIN designacion tit ON tit.id_docente_materia = s.id_designacion_titular "
            "JOIN designacion sup ON sup.id_docente_materia = s.id_designacion_suplente "
            "JOIN docentes dt ON dt.id_docente = tit.id_docente "
            "JOIN docentes ds ON ds.id_docente = sup.id_docente "
            "JOIN materia m ON m.id_materia = tit.id_materia "
            "JOIN carrera c ON c.id_carrera = m.id_carrera "
            "ORDER BY s.id_suplencia DESC")
        hoy_ = date.today()
        items = []
        for f in filas:
            d1, d2 = parse_fecha(f[9]), parse_fecha(f[10])
            if d1 and d1 > hoy_:
                estado, color = "Programada", ft.Colors.ORANGE_800
            elif d2 is None or d2 >= hoy_:
                estado, color = "En curso", ft.Colors.GREEN_700
            else:
                estado, color = "Finalizada", ft.Colors.GREY_600
            if solo_en_curso.value and estado == "Finalizada":
                continue
            items.append(ft.Container(
                padding=ft.Padding.symmetric(horizontal=14, vertical=8),
                border_radius=10,
                border=ft.Border.all(1, ft.Colors.GREY_300),
                content=ft.Row(vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                    ft.Icon(ft.Icons.SWAP_HORIZ, color=COLOR),
                    ft.Column(expand=True, spacing=2, controls=[
                        ft.Text(f"{f[5]}, {f[6]}  cubre a  {f[3]}, {f[4]}",
                                weight=ft.FontWeight.BOLD),
                        ft.Text(f"{f[7]} ({f[8]})  ·  del {f[9]} al {f[10] or '-'}  ·  "
                                f"S.D.N° {f[11] or '-'}" + (f"  ·  {f[2]}" if f[2] else ""),
                                size=12, color=ft.Colors.GREY_700),
                    ]),
                    ft.Text(estado, color=color, weight=ft.FontWeight.W_600),
                    ft.IconButton(icon=ft.Icons.DELETE, tooltip="Eliminar suplencia",
                                  on_click=lambda e, fila=f: eliminar(fila)),
                ]),
            ))
        listado.controls = items
        vacio.visible = not items

    def recargar():
        cargar_opciones()
        cargar_lista()
        page.update()

    # ---------- ALTA ----------
    def agregar(e):
        errores = {}
        dato = designaciones.get(titular.value or "")
        d1, d2 = parse_fecha(desde.value), parse_fecha(hasta.value)
        if not dato:
            errores["titular"] = "Elegí la cátedra a cubrir."
        if not suplente.value:
            errores["suplente"] = "Elegí el suplente."
        elif dato and str(dato["id_docente"]) == suplente.value:
            errores["suplente"] = "El suplente no puede ser el mismo titular."
        if d1 is None:
            errores["desde"] = "Elegí la fecha con el calendario."
        if d2 is None:
            errores["hasta"] = "Elegí la fecha con el calendario."
        elif d1 and d2 < d1:
            errores["hasta"] = "No puede ser anterior a 'Desde'."
        if not (disposicion.value or "").strip():
            errores["disposicion"] = "Ingresá el número de disposición."
        for clave, control in campos.items():
            poner_error(control, errores.get(clave))
        if errores:
            page.update()
            return

        conexion = conectar()
        try:
            with conexion:
                tit = conexion.execute(
                    "SELECT id_materia, turno, anio, division, condicion FROM designacion "
                    "WHERE id_docente_materia = ?", (int(titular.value),)).fetchone()
                cursor = conexion.execute(
                    "INSERT INTO designacion (id_docente, id_materia, fecha_alta, fecha_baja, "
                    "motivo_baja, estado, nro_disposicion, turno, situacion, anio, division, "
                    "condicion, tipo_designacion) "
                    "VALUES (?, ?, ?, ?, 'Fin de suplencia', 'Vigente', ?, ?, 'S', ?, ?, ?, 'Suplencia')",
                    (int(suplente.value), tit[0], desde.value, hasta.value,
                     disposicion.value.strip(), tit[1], tit[2], tit[3], tit[4]))
                conexion.execute(
                    "INSERT INTO suplencia (id_designacion_titular, id_designacion_suplente, motivo) "
                    "VALUES (?, ?, ?)",
                    (int(titular.value), cursor.lastrowid, (motivo.value or "").strip()))
        except sqlite3.Error as error:
            print("Error al guardar la suplencia:", error)
            return avisar(page, "No se pudo guardar la suplencia.")
        finally:
            conexion.close()

        titular.value = suplente.value = None
        hasta.value = disposicion.value = motivo.value = ""
        ayuda_ausencia.visible = False
        refrescar_todo()
        avisar(page, "Suplencia registrada. Ya figura en las designaciones del suplente.")

    def eliminar(f):
        def borrar():
            conexion = conectar()
            try:
                with conexion:
                    # Borrar la designación del suplente borra también la suplencia (cascada)
                    conexion.execute("DELETE FROM designacion WHERE id_docente_materia = ?", (f[1],))
            except sqlite3.Error as error:
                print("Error al eliminar la suplencia:", error)
                return avisar(page, "No se pudo eliminar la suplencia.")
            finally:
                conexion.close()
            refrescar_todo()
            avisar(page, "Suplencia eliminada.")

        confirmar(page, "Eliminar suplencia",
                  f"¿Eliminar la suplencia de {f[5]}, {f[6]} en «{f[7]}»? También se borra su "
                  "designación como suplente. Si la suplencia terminó, no hace falta borrarla: "
                  "queda como 'Finalizada' en el historial.",
                  borrar, texto_boton="Eliminar")

    registrar(recargar)
    cargar_opciones()
    cargar_lista()
    return _columna([
        tarjeta_formulario(
            "Nueva suplencia", ft.Icons.SWAP_HORIZ, COLOR,
            [titular, suplente, fila_desde, fila_hasta, disposicion, motivo, ayuda_ausencia,
             ft.Button(content=ft.Text("Registrar suplencia"), icon=ft.Icons.ADD, on_click=agregar)],
            ayuda="Elegí la cátedra del docente que se ausenta y quién lo reemplaza. Los docentes "
                  "que hoy están de licencia o con carpeta médica aparecen marcados como AUSENTE HOY."),
        _lista("Suplencias", ft.Icons.ACCOUNT_TREE, COLOR, [solo_en_curso, listado, vacio]),
    ])
