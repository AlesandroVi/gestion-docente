"""Piezas de interfaz y utilidades compartidas por todas las pantallas."""
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import flet as ft

from database.consultas import FORMATO_FECHA, parse_fecha


# ---------- ARCHIVOS ----------

def carpeta_descargas():
    carpeta = Path.home() / "Downloads"
    carpeta.mkdir(exist_ok=True)
    return carpeta


def abrir_archivo(ruta):
    """Abre un archivo con el programa del sistema (por ejemplo, el visor de PDF)."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(ruta)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(ruta)])
        else:
            subprocess.Popen(["xdg-open", str(ruta)])
    except Exception as error:
        print("No se pudo abrir el archivo:", error)


# ---------- AVISOS Y DIÁLOGOS ----------

def avisar(page: ft.Page, mensaje):
    page.show_dialog(ft.SnackBar(ft.Text(mensaje)))


def cerrar_dialogo(page: ft.Page, dialogo):
    dialogo.open = False
    page.update()


def mostrar_mensaje(page: ft.Page, titulo, mensaje):
    dialogo = None

    def cerrar(e):
        cerrar_dialogo(page, dialogo)

    dialogo = ft.AlertDialog(
        modal=True,
        title=ft.Text(titulo),
        content=ft.Text(mensaje),
        actions=[ft.Button(content=ft.Text("Entendido"), on_click=cerrar)],
    )
    page.show_dialog(dialogo)


def confirmar(page: ft.Page, titulo, mensaje, al_confirmar,
              texto_boton="Confirmar", al_cancelar=None):
    dialogo = None

    def cancelar(e):
        cerrar_dialogo(page, dialogo)
        if al_cancelar:
            al_cancelar()

    def aceptar(e):
        cerrar_dialogo(page, dialogo)
        al_confirmar()

    dialogo = ft.AlertDialog(
        modal=True,
        title=ft.Text(titulo),
        content=ft.Text(mensaje),
        actions=[
            ft.TextButton("Cancelar", on_click=cancelar),
            ft.Button(content=ft.Text(texto_boton), on_click=aceptar),
        ],
    )
    page.show_dialog(dialogo)


# ---------- CAMPOS ----------

def _nombre_error(control):
    """Según la versión de Flet, el cartel rojo se guarda en `error` o en `error_text`."""
    for nombre in ("error_text", "error"):
        if hasattr(control, nombre):
            return nombre
    return None


def poner_error(control, mensaje):
    """Muestra (o quita, con None) el mensaje de error en rojo de un campo."""
    nombre = _nombre_error(control)
    if nombre:
        setattr(control, nombre, mensaje)


def obtener_error(control):
    nombre = _nombre_error(control)
    return getattr(control, nombre, None) if nombre else None


def solo_numeros():
    """Filtro para que un campo solo acepte dígitos (None si esta versión no lo trae)."""
    filtro = getattr(ft, "NumbersOnlyInputFilter", None)
    return filtro() if filtro else None


def _opcion(clave, texto):
    clase = getattr(ft, "DropdownOption", None) or ft.dropdown.Option
    return clase(key=str(clave), text=str(texto))


def desplegable(etiqueta, opciones, valor=None, ancho=None, icono=None):
    """Lista desplegable. `opciones`: textos, o tuplas (clave, texto).

    Escucha el evento de selección para que Python reciba siempre la opción elegida
    y para quitar el cartel rojo de error apenas el usuario elige algo."""
    lista = ft.Dropdown(
        label=etiqueta,
        options=_armar_opciones(opciones),
        value=None if valor is None else str(valor),
        width=ancho,
    )

    def al_elegir(e):
        control = e.control
        elegido = control.value
        if elegido in (None, ""):
            dato = getattr(e, "data", None)
            if isinstance(dato, str) and dato in {str(o.key) for o in control.options}:
                elegido = dato
        control.value = elegido
        poner_error(control, None)
        control.update()

    # Según la versión de Flet el evento se llama on_select u on_change: se escuchan ambos.
    lista.on_select = al_elegir
    lista.on_change = al_elegir
    return lista


def _armar_opciones(opciones):
    items = []
    for o in opciones:
        clave, texto = o if isinstance(o, tuple) else (o, o)
        items.append(_opcion(clave, texto))
    return items


def actualizar_opciones(desplegable_, opciones, valor=None):
    desplegable_.options = _armar_opciones(opciones)
    desplegable_.value = None if valor is None else str(valor)


def campo_fecha(page: ft.Page, etiqueta, valor="", ancho=None,
                primera=None, ultima=None, inicial=None, permitir_borrar=False):
    """Campo de fecha con calendario. Devuelve (fila, campo); el texto queda en campo.value
    con formato dd/mm/aaaa."""
    hoy = date.today()
    primera = primera or date(hoy.year - 100, 1, 1)
    ultima = ultima or date(hoy.year + 10, 12, 31)

    campo = ft.TextField(
        label=etiqueta,
        value=valor or "",
        hint_text="dd/mm/aaaa",
        read_only=True,
        expand=True,
    )

    def al_elegir(e):
        elegido = e.control.value
        if elegido:
            campo.value = elegido.strftime(FORMATO_FECHA)
            poner_error(campo, None)
            page.update()

    def abrir(e):
        base = parse_fecha(campo.value) or inicial or hoy
        base = min(max(base, primera), ultima)
        page.show_dialog(
            ft.DatePicker(
                value=datetime(base.year, base.month, base.day),
                first_date=datetime(primera.year, primera.month, primera.day),
                last_date=datetime(ultima.year, ultima.month, ultima.day),
                on_change=al_elegir,
            )
        )

    def borrar(e):
        campo.value = ""
        page.update()

    controles = [
        campo,
        ft.IconButton(icon=ft.Icons.CALENDAR_MONTH, tooltip="Elegir fecha", on_click=abrir),
    ]
    if permitir_borrar:
        controles.append(ft.IconButton(icon=ft.Icons.CLOSE, tooltip="Quitar fecha", on_click=borrar))

    return ft.Row(controls=controles, spacing=4, width=ancho), campo


def autolimpiar(*campos):
    """Cada campo saca su cartel rojo apenas el usuario lo modifica."""
    for campo in campos:
        if isinstance(campo, ft.Dropdown):
            continue  # el desplegable ya lo hace por su cuenta

        def al_cambiar(e):
            if obtener_error(e.control):
                poner_error(e.control, None)
                e.control.update()

        campo.on_change = al_cambiar


def resumen_errores(errores, nombres):
    """'Revisá: Nombre, DNI.' a partir de {campo: mensaje} y {campo: etiqueta}."""
    lista = [nombres.get(clave, clave) for clave in errores]
    return "Revisá estos campos: " + ", ".join(lista) + "."


def _esquinas_superiores(radio):
    fabrica = getattr(ft.BorderRadius, "only", None)
    return fabrica(top_left=radio, top_right=radio) if fabrica else radio


def encabezado_seccion(titulo, icono, color):
    """Franja de color con icono y título para las tarjetas de formulario."""
    return ft.Container(
        content=ft.Row(
            controls=[ft.Icon(icono, color=ft.Colors.WHITE, size=22),
                      ft.Text(titulo, color=ft.Colors.WHITE, size=16, weight=ft.FontWeight.BOLD)],
            spacing=10),
        bgcolor=color,
        padding=ft.Padding.symmetric(horizontal=18, vertical=10),
        border_radius=_esquinas_superiores(12),
    )


def tarjeta_formulario(titulo, icono, color, controles, ayuda=None):
    """Tarjeta con franja de color y los campos del formulario adentro."""
    cuerpo = []
    if ayuda:
        cuerpo.append(ft.Text(ayuda, size=12, color=ft.Colors.GREY_700))
    cuerpo.append(ft.Row(controls=controles, wrap=True, spacing=14, run_spacing=14,
                         vertical_alignment=ft.CrossAxisAlignment.START))
    return ft.Container(
        content=ft.Column(
            controls=[
                encabezado_seccion(titulo, icono, color),
                ft.Container(content=ft.Column(controls=cuerpo, spacing=12), padding=18),
            ],
            spacing=0,
        ),
        border_radius=12,
        border=ft.Border.all(1, color),
        bgcolor=ft.Colors.with_opacity(0.04, color),
    )


def campo(etiqueta, icono=None, ancho=None, **kw):
    """TextField con el estilo del sistema (relleno, bordes redondeados e icono)."""
    return ft.TextField(label=etiqueta, prefix_icon=icono, width=ancho,
                        filled=True, border_radius=10, **kw)


def ocultar_error_al_escribir(page, texto_error, *campos):
    """Oculta el mensaje de error de un diálogo apenas el usuario cambia algún campo."""
    for campo_ in campos:
        def al_cambiar(e):
            if texto_error.visible:
                texto_error.visible = False
                page.update()
        campo_.on_change = al_cambiar
