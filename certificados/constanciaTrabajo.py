"""Constancia de trabajo con la tabla de cátedras (modelo del I.C.S. N° 6034)."""
import flet as ft
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from certificados.comun import (
    abrir_archivo, avisar, bloque_firma, carpeta_descargas, encabezado_institucional,
    formato_dni, frase_expedicion, frase_suscribe, nombre_constancia, parrafo_numero, texto,
    vista_selector_docentes,
)
from herramientas.registro import emitir
from database.consultas import designaciones_constancia, es_vigente

MARGEN = 1.5 * cm
ANCHO_UTIL = A4[0] - 2 * MARGEN

ESTILO_TITULO = ParagraphStyle("tit_trabajo", fontName="Helvetica-Bold", fontSize=12,
                               leading=16, alignment=TA_CENTER)
ESTILO_TEXTO = ParagraphStyle("txt_trabajo", fontName="Helvetica", fontSize=11, leading=17,
                              alignment=TA_JUSTIFY, firstLineIndent=1.5 * cm)
ESTILO_CIERRE = ParagraphStyle("cierre_trabajo", parent=ESTILO_TEXTO, firstLineIndent=0)
ESTILO_CELDA = ParagraphStyle("celda", fontName="Helvetica", fontSize=8, leading=10,
                              alignment=TA_CENTER)
ESTILO_CABECERA = ParagraphStyle("cabecera", parent=ESTILO_CELDA, fontSize=9, leading=11)

COLUMNAS = ["Espacio curricular", "Carrera", "T", "S", "Horas", "Año", "Div.", "C",
            "Toma de Posesión", "Baja", "Observaciones", ""]
ANCHOS = [3.0, 3.3, 0.55, 0.55, 1.0, 0.8, 0.8, 0.8, 1.8, 1.8, 1.4, 2.2]


def _carrera(fila):
    """'Tec. Sup. en ... Res. Min. 903/11.'"""
    carrera = str(fila["carrera"]).strip().rstrip(".")
    resolucion = str(fila["resolucion"] or "").strip().rstrip(".")
    if not resolucion:
        return carrera + "."
    if not resolucion.lower().startswith("res"):
        resolucion = f"Res. Min. {resolucion}"
    return f"{carrera}. {resolucion}."


def _observacion(fila):
    """'Alta. Designación a término.' o 'Baja. Designación a término.'"""
    tipo = (fila["tipo_designacion"] or "Designación a término").strip().rstrip(".")
    if es_vigente(fila["baja"]):
        return f"Alta. {tipo}."
    motivo = (fila["motivo_baja"] or tipo).strip().rstrip(".")
    return f"Baja. {motivo}."


def tabla_catedras(designaciones):
    def celda(valor, estilo=ESTILO_CELDA):
        return Paragraph(texto(valor if valor not in (None, "") else "-"), estilo)

    datos = [[celda(c, ESTILO_CABECERA) for c in COLUMNAS]]
    for f in designaciones:
        datos.append([
            celda(f["materia"]), celda(_carrera(f)), celda(f["turno"]), celda(f["situacion"]),
            celda(f["horas"]), celda(f["anio"]), celda(f["division"]), celda(f["condicion"]),
            celda(f["alta"]), celda(f["baja"]), celda(f"S.D.N° {f['disposicion']}"),
            celda(_observacion(f)),
        ])

    escala = ANCHO_UTIL / (sum(ANCHOS) * cm)
    tabla = Table(datos, colWidths=[a * cm * escala for a in ANCHOS], repeatRows=1)
    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
        ("SPAN", (10, 0), (11, 0)),  # "Observaciones" ocupa las dos últimas columnas
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    return tabla


def crear_constancia_trabajo(d, designaciones, ruta, numero=None):
    """`d`: fila del docente. `designaciones`: lista de designaciones_constancia(dni)."""
    doc = SimpleDocTemplate(ruta, pagesize=A4, leftMargin=MARGEN, rightMargin=MARGEN,
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm)

    vigentes = [f for f in designaciones if es_vigente(f["baja"])]
    verbo = "se desempeña" if (vigentes or not designaciones) else "se desempeñó"
    cierre = "en las siguientes cátedras:" if designaciones else "."

    intro = (
        f"{frase_suscribe()} <b>CERTIFICA QUE {texto(nombre_constancia(d))}, "
        f"DNI N° {texto(formato_dni(d[0]))}</b> {verbo} como Profesor "
        f"{texto(d[7])} en este establecimiento {cierre}"
    )

    contenido = encabezado_institucional(ANCHO_UTIL) + [
        Paragraph("CONSTANCIA DE TRABAJO", ESTILO_TITULO),
    ] + parrafo_numero(numero) + [
        Spacer(1, 0.6 * cm),
        Paragraph(intro, ESTILO_TEXTO),
        Spacer(1, 0.3 * cm),
    ]
    if designaciones:
        contenido += [tabla_catedras(designaciones), Spacer(1, 0.6 * cm)]

    contenido += [
        Paragraph(frase_expedicion(), ESTILO_CIERRE),
        bloque_firma(),
    ]
    doc.build(contenido)


def vista_constancia_trabajo(page: ft.Page):

    def generar(d):
        try:
            ruta = str(carpeta_descargas() / f"constancia_trabajo_{d[0]}.pdf")
            designaciones = designaciones_constancia(d[0])
            numero = emitir(
                "Trabajo", d, ruta,
                lambda n: crear_constancia_trabajo(d, designaciones, ruta, numero=n),
                detalle=f"{len(designaciones)} cátedra(s)")
            avisar(page, f"Constancia N° {numero} guardada en: {ruta}")
            abrir_archivo(ruta)
        except PermissionError:
            avisar(page, "No se pudo guardar: cerrá el PDF si lo tenés abierto.")
        except Exception as error:
            print("Error al generar la constancia de trabajo:", error)
            avisar(page, "No se pudo generar la constancia")

    return vista_selector_docentes(
        page,
        titulo="Constancias de trabajo",
        subtitulo="Buscá al docente y generá su constancia. Se guarda en Descargas y se abre para imprimir.",
        icono=ft.Icons.WORK,
        texto_boton="Generar constancia",
        icono_boton=ft.Icons.PICTURE_AS_PDF,
        accion=generar,
        color=ft.Colors.TEAL_700,
        incluir_inactivos=True,  # un ex docente puede necesitar su constancia
    )
