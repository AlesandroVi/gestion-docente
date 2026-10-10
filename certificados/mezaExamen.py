import re
from datetime import date

import flet as ft
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from certificados.comun import (
    ESTILO_CUERPO, ESTILO_TITULO,
    abrir_archivo, avisar, bloque_firma, carpeta_descargas, encabezado_institucional,
    fecha_en_letras, formato_dni, frase_expedicion, frase_suscribe, nombre_constancia, texto,
    parrafo_numero, vista_selector_docentes,
)
from herramientas.registro import emitir
from database import ajustes
from database.consultas import FORMATO_FECHA, parse_fecha
from ui import campo_fecha, cerrar_dialogo, ocultar_error_al_escribir

RE_HORA = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def normalizar_hora(valor):
    """'9:30' -> '09:30'. Devuelve None si no es una hora válida."""
    m = RE_HORA.match((valor or "").strip())
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else None


def crear_constancia(nombre, dni, fecha_examen, desde, hasta, ruta, numero=None):
    doc = SimpleDocTemplate(ruta, pagesize=landscape(A4),
                            leftMargin=3 * cm, rightMargin=3 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm)

    if fecha_examen == date.today():
        cuando = "en el día de la fecha"
    else:
        cuando = f"el día <u>{fecha_en_letras(fecha_examen)}</u>"

    doc.build(encabezado_institucional(landscape(A4)[0] - 6 * cm) + [
        Paragraph("<u>CONSTANCIA DE EXAMEN</u>", ESTILO_TITULO),
    ] + parrafo_numero(numero) + [
        Spacer(1, 0.8 * cm),
        Paragraph(
            f"{frase_suscribe()} "
            f"<b>CERTIFICA QUE {texto(nombre)}, DNI N° {texto(formato_dni(dni))}</b> "
            f"conformó parte del Tribunal de Mesa de Examen Final {cuando}, "
            f"desde las <u>{desde}</u> hs hasta las <u>{hasta}</u> hs.", ESTILO_CUERPO),
        Spacer(1, 0.5 * cm),
        Paragraph(frase_expedicion(), ESTILO_CUERPO),
        bloque_firma(),
    ])


def vista_mesas_examen(page: ft.Page):

    def abrir_formulario(d):
        ancho = 380
        hoy = date.today()
        fila_fecha, fecha = campo_fecha(
            page, "Fecha del examen", valor=hoy.strftime(FORMATO_FECHA), ancho=ancho,
            primera=date(hoy.year - 2, 1, 1), ultima=date(hoy.year + 1, 12, 31), inicial=hoy,
        )
        desde = ft.TextField(label="Hora de inicio (hh:mm)", width=ancho // 2 - 6,
                             value=ajustes.obtener("examen_hora_desde"))
        hasta = ft.TextField(label="Hora de fin (hh:mm)", width=ancho // 2 - 6,
                             value=ajustes.obtener("examen_hora_hasta"))
        error = ft.Text(color=ft.Colors.RED_700, visible=False)
        ocultar_error_al_escribir(page, error, desde, hasta)

        def mostrar_error(mensaje):
            error.value = mensaje
            error.visible = True
            page.update()

        def generar(e):
            dia = parse_fecha(fecha.value)
            h1, h2 = normalizar_hora(desde.value), normalizar_hora(hasta.value)
            if dia is None:
                return mostrar_error("Elegí la fecha del examen con el calendario.")
            if not h1 or not h2:
                return mostrar_error("Las horas deben tener el formato hh:mm (ej: 19:30).")
            if h1 >= h2:
                return mostrar_error("La hora de fin debe ser posterior a la de inicio.")

            try:
                ruta = str(carpeta_descargas() / f"constancia_examen_{d[0]}_{dia:%Y%m%d}.pdf")
                numero = emitir(
                    "Examen", d, ruta,
                    lambda n: crear_constancia(nombre_constancia(d), str(d[0]), dia, h1, h2, ruta,
                                               numero=n),
                    detalle=f"Mesa del {dia.strftime(FORMATO_FECHA)} de {h1} a {h2}")
            except PermissionError:
                return mostrar_error("No se pudo guardar: cerrá el PDF si lo tenés abierto.")
            except Exception as err:
                print("Error al generar la constancia:", err)
                return mostrar_error("No se pudo generar la constancia.")

            cerrar_dialogo(page, dialogo)
            avisar(page, f"Constancia N° {numero} guardada en: {ruta}")
            abrir_archivo(ruta)

        dialogo = None
        dialogo = ft.AlertDialog(
            modal=True,
            title=ft.Text("Constancia de examen"),
            content=ft.Column(
                controls=[
                    ft.Text(f"{d[2]}, {d[1]} - DNI {d[0]}", weight=ft.FontWeight.BOLD),
                    fila_fecha,
                    ft.Row(controls=[desde, hasta], spacing=12),
                    error,
                ],
                tight=True, width=ancho + 20, spacing=14,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: cerrar_dialogo(page, dialogo)),
                ft.Button(content=ft.Text("Generar PDF"), icon=ft.Icons.PICTURE_AS_PDF, on_click=generar),
            ],
        )
        page.show_dialog(dialogo)

    return vista_selector_docentes(
        page,
        titulo="Constancias de examen",
        subtitulo="Elegí al docente, la fecha y el horario del examen. Se guarda en Descargas y se abre para imprimir.",
        icono=ft.Icons.EVENT_NOTE,
        texto_boton="Generar constancia",
        icono_boton=ft.Icons.PICTURE_AS_PDF,
        accion=abrir_formulario,
        color=ft.Colors.ORANGE_800,
    )
