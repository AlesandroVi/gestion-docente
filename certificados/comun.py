import sqlite3  # noqa: F401  (se mantiene por compatibilidad)
from datetime import date
from html import escape

import flet as ft
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Image, KeepTogether, Paragraph, Spacer, Table, TableStyle

from config import CARPETA_LOGOS
from database import ajustes
from database.consultas import listar_docentes
# Se reexportan para que los certificados las importen desde acá.
from ui import abrir_archivo, avisar, carpeta_descargas  # noqa: F401

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

ESTILO_ENCABEZADO = ParagraphStyle("enc", fontName="Helvetica-BoldOblique",
                                   fontSize=12, leading=16, alignment=TA_CENTER)
ESTILO_TITULO = ParagraphStyle("tit", fontName="Helvetica-Bold",
                               fontSize=15, leading=20, alignment=TA_CENTER)
ESTILO_CUERPO = ParagraphStyle("cuerpo", fontName="Helvetica",
                               fontSize=12, leading=24, alignment=TA_JUSTIFY)
ESTILO_LISTA = ParagraphStyle("lista", fontName="Helvetica",
                              fontSize=12, leading=18, leftIndent=1 * cm,
                              bulletIndent=0.4 * cm)
ESTILO_FIRMA = ParagraphStyle("firma", fontName="Helvetica",
                              fontSize=10, leading=13, alignment=TA_CENTER)


def texto(valor):
    """Escapa un valor para usarlo dentro de un Paragraph de reportlab."""
    return escape(str(valor))


def fecha_hoy(fecha=None):
    """Devuelve (día, mes en letras, año con formato 2.026). Sin argumento, usa hoy."""
    fecha = fecha or date.today()
    return fecha.day, MESES[fecha.month - 1], f"{fecha.year:,}".replace(",", ".")


_UNIDADES = ["cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho",
             "nueve", "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis",
             "diecisiete", "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós",
             "veintitrés", "veinticuatro", "veinticinco", "veintiséis", "veintisiete",
             "veintiocho", "veintinueve"]
_DECENAS = {3: "treinta", 4: "cuarenta", 5: "cincuenta", 6: "sesenta",
            7: "setenta", 8: "ochenta", 9: "noventa"}


def numero_en_letras(numero, apocope=False):
    """0 a 99 en letras. Con `apocope=True` 'uno' pasa a 'un' (veintiún días, treinta y un días)."""
    if numero < 30:
        letras = _UNIDADES[numero]
    else:
        decena, unidad = divmod(numero, 10)
        letras = _DECENAS[decena] + (f" y {_UNIDADES[unidad]}" if unidad else "")
    if apocope and letras.endswith("uno"):
        letras = letras[:-3] + ("ún" if letras == "veintiuno" else "un")
    return letras


def dia_en_letras(dia):
    """10 -> 'diez (10)'."""
    return f"{numero_en_letras(dia)} ({dia})"


def fecha_en_letras(fecha):
    """date -> 'diez (10) de octubre de 2.026'."""
    anio = f"{fecha.year:,}".replace(",", ".")
    return f"{dia_en_letras(fecha.day)} de {MESES[fecha.month - 1]} de {anio}"


# ---------- DATOS DE LA INSTITUCIÓN (se editan en "Ajustes") ----------

ESTILO_INSTITUTO = ParagraphStyle("inst", fontName="Times-Bold", fontSize=13, leading=17,
                                  alignment=TA_CENTER)


def _logo(nombre, ancho, alto):
    """Imagen de la carpeta "logos" (o un espacio vacío si no está)."""
    for extension in (".png", ".jpg", ".jpeg"):
        ruta = CARPETA_LOGOS / f"{nombre}{extension}"
        if ruta.exists():
            try:
                imagen = Image(str(ruta))
                escala = min(ancho / imagen.imageWidth, alto / imagen.imageHeight)
                imagen.drawWidth = imagen.imageWidth * escala
                imagen.drawHeight = imagen.imageHeight * escala
                return imagen
            except Exception as error:
                print(f"No se pudo usar el logo {ruta}:", error)
    return ""


def encabezado_institucional(ancho_total=16 * cm):
    """Logo izquierdo | logo del instituto + nombre | logo derecho."""
    cfg = ajustes.institucion()
    lineas = [l.strip() for l in cfg["inst_encabezado"].splitlines() if l.strip()]
    nombre = Paragraph("<br/>".join(texto(l) for l in lineas), ESTILO_INSTITUTO)
    centro = _logo("logo_centro", 2.2 * cm, 2.2 * cm)
    columna_centro = [centro, Spacer(1, 0.15 * cm), nombre] if centro else [nombre]

    lateral = 4.2 * cm
    tabla = Table(
        [[_logo("logo_izquierdo", lateral, 2 * cm), columna_centro,
          _logo("logo_derecho", lateral, 2 * cm)]],
        colWidths=[lateral, ancho_total - 2 * lateral, lateral],
    )
    tabla.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return [tabla, Spacer(1, 0.9 * cm)]


def frase_suscribe():
    """'La que suscribe: Prosecretaria del Instituto ..., Prof. Nombre Apellido.'"""
    cfg = ajustes.institucion()
    return (f"La que suscribe: {texto(cfg['firmante_cargo'])} del {texto(cfg['inst_nombre'])}, "
            f"{texto(cfg['firmante_nombre'])}.")


def formato_dni(dni):
    """30123456 -> '30.123.456'."""
    digitos = "".join(ch for ch in str(dni) if ch.isdigit())
    return f"{int(digitos):,}".replace(",", ".") if digitos else str(dni)


def nombre_constancia(d):
    """'PÉREZ, Juan Carlos'."""
    nombre = " ".join(p.capitalize() for p in str(d[1]).split())
    return f"{str(d[2]).upper()}, {nombre}"


def frase_fecha(fecha=None):
    """'En la localidad de El Galpón, a los días tres (3) del mes de junio de 2.026.'"""
    cfg = ajustes.institucion()
    dia, mes, anio = fecha_hoy(fecha)
    cuando = "al día primero (1)" if dia == 1 else f"a los días {numero_en_letras(dia)} ({dia})"
    return (f"En la localidad de {texto(cfg['localidad'])}, {cuando} "
            f"del mes de {mes} de {anio}.")


def frase_expedicion(final="", fecha=None):
    """Cierre de todas las constancias, como el modelo de la institución:
    '-----A solicitud del interesado se extiende la PTE. Constancia ... de 2.026.-----'"""
    return ("-" * 14 + "A solicitud del interesado se extiende la PTE. Constancia para ser "
            "presentada ante autoridades que así lo requieran. "
            + frase_fecha(fecha) + "-" * 30)


ESTILO_NUMERO = ParagraphStyle("numero", fontName="Helvetica", fontSize=9, leading=12,
                              alignment=TA_RIGHT)


def parrafo_numero(numero):
    """'Constancia N° 15/2026' arriba a la derecha (nada si no hay número)."""
    if not numero:
        return []
    return [Paragraph(f"Constancia N° <b>{texto(numero)}</b>", ESTILO_NUMERO)]


def bloque_firma():
    """Espacio para firma y sello al pie (se imprime y se firma a mano)."""
    cfg = ajustes.institucion()
    firma = Paragraph(f"{texto(cfg['firmante_nombre'])}<br/>{texto(cfg['firmante_cargo'])}",
                      ESTILO_FIRMA)
    sello = Paragraph("Sello de la institución", ESTILO_FIRMA)
    tabla = Table([["", "", ""], [firma, "", sello]],
                  colWidths=[6.5 * cm, 2 * cm, 6.5 * cm],
                  rowHeights=[2.4 * cm, None])
    tabla.setStyle(TableStyle([
        ("LINEABOVE", (0, 1), (0, 1), 0.8, colors.black),
        ("LINEABOVE", (2, 1), (2, 1), 0.8, colors.black),
        ("VALIGN", (0, 1), (-1, 1), "TOP"),
    ]))
    return KeepTogether([Spacer(1, 1.2 * cm), tabla])


# ---------- PANTALLA DE SELECCIÓN DE DOCENTE ----------

def vista_selector_docentes(page: ft.Page, titulo, subtitulo, icono, texto_boton,
                            icono_boton, accion, color=ft.Colors.BLUE_700,
                            incluir_inactivos=False, acciones_extra=None):
    """Pantalla con buscador + tabla de docentes y botones por fila.

    `accion(d)` recibe la fila completa del docente:
    d[0] dni | d[1] nombre | d[2] apellido | d[3] cuil
    d[4] fecha_nacimiento | d[5] domicilio | d[6] email | d[7] caracter | d[8] activo

    `acciones_extra`: lista de (icono, ayuda, función(d)) para botones adicionales.
    """

    tabla = ft.DataTable(
        columns=[
            ft.DataColumn(label=ft.Text("DNI", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(label=ft.Text("Apellido y nombre", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(label=ft.Text("Carácter", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(label=ft.Text("Acción", weight=ft.FontWeight.BOLD)),
        ],
        rows=[],
        column_spacing=60,
        heading_row_height=50,
        data_row_min_height=56,
        divider_thickness=0.5,
    )

    contador = ft.Text(size=13, color=ft.Colors.GREY_600)
    sin_resultados = ft.Text(
        "No se encontraron docentes", size=16, color=ft.Colors.GREY_600, visible=False
    )

    buscador = ft.TextField(
        label="Buscar por DNI, nombre o apellido",
        prefix_icon=ft.Icons.SEARCH,
        width=420,
        border_radius=10,
        on_change=lambda e: cargar_tabla(buscador.value),
    )

    def cargar_tabla(filtro=""):
        docentes = listar_docentes(filtro, incluir_inactivos=incluir_inactivos)

        filas = []
        for d in docentes:
            botones = [
                ft.Button(
                    content=ft.Text(texto_boton),
                    icon=icono_boton,
                    on_click=lambda e, doc=d: accion(doc),
                )
            ]
            for ic, ayuda, funcion in (acciones_extra or []):
                botones.append(ft.IconButton(
                    icon=ic, tooltip=ayuda,
                    on_click=lambda e, doc=d, f=funcion: f(doc)))

            nombre = f"{d[2]}, {d[1]}" + ("" if d[8] else " (inactivo)")
            filas.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(d[0]))),
                ft.DataCell(ft.Text(nombre)),
                ft.DataCell(ft.Text(str(d[7]))),
                ft.DataCell(ft.Row(controls=botones, spacing=6)),
            ]))

        tabla.rows = filas
        tabla.visible = len(docentes) > 0
        sin_resultados.visible = len(docentes) == 0
        contador.value = f"{len(docentes)} docente(s)"
        page.update()

    cargar_tabla()

    encabezado = ft.Row(
        controls=[
            ft.Icon(icono, size=36, color=color),
            ft.Column(
                controls=[
                    ft.Text(titulo, size=28, weight=ft.FontWeight.BOLD),
                    ft.Text(subtitulo, size=14, color=ft.Colors.GREY_600),
                ],
                spacing=2,
            ),
        ],
        spacing=15,
    )

    tarjeta = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        buscador,
                        ft.IconButton(
                            icon=ft.Icons.REFRESH,
                            tooltip="Actualizar tabla",
                            on_click=lambda e: cargar_tabla(buscador.value),
                        ),
                        ft.Container(expand=True),
                        contador,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Divider(),
                ft.Row(controls=[tabla], scroll=ft.ScrollMode.AUTO),
                sin_resultados,
            ],
            spacing=15,
        ),
        padding=25,
        border_radius=12,
        border=ft.Border.all(1, ft.Colors.GREY_300),
    )

    return ft.Column(
        controls=[encabezado, tarjeta],
        spacing=25,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
