import sqlite3
from datetime import date, timedelta

import flet as ft
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from certificados.comun import (
    abrir_archivo, avisar, carpeta_descargas, encabezado_institucional, formato_dni,
    nombre_constancia, parrafo_numero, texto, vista_selector_docentes,
)
from herramientas.registro import emitir
from config import TIPOS_PEDIDO_MEDICO
from database import ajustes
from database.conexion import conectar
from database.consultas import FORMATO_FECHA, certificados_de, designaciones_de, parse_fecha
from ui import (
    campo_fecha, cerrar_dialogo, confirmar, desplegable, ocultar_error_al_escribir, solo_numeros,
)

FORMATO = FORMATO_FECHA


ESTILO_FORM_TITULO = ParagraphStyle("sol_tit", fontName="Helvetica-Bold", fontSize=14,
                                    leading=18, alignment=TA_CENTER)
ESTILO_FORM_SUB = ParagraphStyle("sol_sub", fontName="Helvetica-Bold", fontSize=11,
                                 leading=14, alignment=TA_CENTER)
ESTILO_FORM = ParagraphStyle("sol", fontName="Helvetica", fontSize=10.5, leading=15)
ESTILO_FORM_CENTRO = ParagraphStyle("sol_centro", parent=ESTILO_FORM, alignment=TA_CENTER)
ESTILO_FORM_CHICO = ParagraphStyle("sol_chico", fontName="Helvetica", fontSize=7, leading=9,
                                   alignment=TA_CENTER)
ANCHO_FORM = 17 * cm


def _casilla(marcada):
    """Cuadradito para marcar con una X."""
    caja = Table([["X" if marcada else ""]], colWidths=[0.55 * cm], rowHeights=[0.55 * cm])
    caja.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return caja


def _recuadro(filas, grosor=1.2):
    """Bloque con borde, una fila por renglón del formulario."""
    tabla = Table([[f] for f in filas], colWidths=[ANCHO_FORM])
    tabla.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), grosor, colors.black),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return tabla


def _renglon(etiqueta, valor):
    return Paragraph(f"<b>{etiqueta}</b> {texto(valor) if valor else ''}", ESTILO_FORM)


def crear_certificado_medico(d, inicio, dias, medico, matricula, observaciones, ruta,
                             fecha_emision=None, tipo_pedido="", parentesco="", funcion="",
                             horario="", numero=None):
    """Solicitud de licencia médica para el personal (modelo del I.C.S. N° 6034).
    `fecha_emision` (date) es la fecha del pedido; sirve para reimprimir con la fecha original."""
    cfg = ajustes.institucion()
    fin = inicio + timedelta(days=dias - 1)
    pedido = fecha_emision or date.today()
    unidad = "día" if dias == 1 else "días"
    caracter = str(d[7]).lower()

    organismo = _recuadro([
        Spacer(1, 0.15 * cm),
        _renglon("ORGANISMO:", cfg["organismo"]),
        _renglon("DEPENDENCIA:", cfg["dependencia"]),
        Spacer(1, 0.3 * cm),
    ])

    # Fila "Agente Interino [ ] | Agente Suplente [ ]"
    agente = Table(
        [[Paragraph("Agente Interino", ESTILO_FORM_CENTRO), _casilla(caracter == "interino"),
          Paragraph("Agente Suplente", ESTILO_FORM_CENTRO), _casilla(caracter == "suplente")]],
        colWidths=[5.5 * cm, 2.6 * cm, 5.5 * cm, 3.4 * cm],
    )
    agente.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    datos_agente = Table(
        [[agente],
         [Paragraph("(marcar con una X)", ESTILO_FORM_CHICO)],
         [_renglon("APELLIDOS Y NOMBRES:", nombre_constancia(d))],
         [_renglon("D.N.I. Nº:", formato_dni(d[0]))],
         [_renglon("CUIL N° :", d[3])],
         [_renglon("FECHA NACIMIENTO:", d[4])],
         [_renglon("DOMICILIO ACTUAL:", d[5])],
         [Spacer(1, 0.4 * cm)]],
        colWidths=[ANCHO_FORM],
    )
    datos_agente.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1.2, colors.black),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 0),
        ("TOPPADDING", (0, 0), (0, 0), 0),
        ("LEFTPADDING", (0, 2), (-1, -1), 10),
        ("TOPPADDING", (0, 1), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 1),
    ]))

    extension = (f"{dias} {unidad}, desde el {inicio.strftime(FORMATO)} "
                 f"hasta el {fin.strftime(FORMATO)} inclusive")
    datos_pedido = _recuadro([
        Spacer(1, 0.15 * cm),
        _renglon("FECHA PEDIDO:", pedido.strftime(FORMATO)),
        _renglon("FUNCIÓN QUE CUMPLE:", funcion),
        _renglon("HORARIO DE TRABAJO:", horario),
        _renglon("Extensión:", extension),
        Spacer(1, 0.3 * cm),
    ])

    tipo = (tipo_pedido or "").lower()
    tipo_tabla = Table(
        [[Paragraph("(marcar con una X)", ESTILO_FORM_CHICO), "", "", "", ""],
         [Paragraph("<b>TIPO DE PEDIDO:</b>", ESTILO_FORM), Paragraph("Consultorio:", ESTILO_FORM),
          _casilla(tipo == "consultorio"), Paragraph("<b>Domicilio :</b>", ESTILO_FORM),
          _casilla(tipo == "domicilio")],
         ["", Paragraph("Atención Familiar:", ESTILO_FORM), _casilla(tipo == "atención familiar"),
          Paragraph(f"<b>Parentesco:</b> {texto(parentesco or '')}", ESTILO_FORM), ""]],
        colWidths=[3.6 * cm, 4.6 * cm, 1.2 * cm, 6.2 * cm, 1.4 * cm],
    )
    tipo_tabla.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1.2, colors.black),
        ("SPAN", (0, 0), (1, 0)),
        ("SPAN", (3, 2), (4, 2)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
    ]))

    detalle = []
    if medico:
        profesional = texto(medico) + (f" (Mat. N° {texto(matricula)})" if matricula else "")
        detalle.append(Paragraph(f"<b>MÉDICO/A:</b> {profesional}", ESTILO_FORM))
    if observaciones:
        detalle.append(Paragraph(f"<b>OBSERVACIONES:</b> {texto(observaciones)}", ESTILO_FORM))

    contenido = encabezado_institucional(ANCHO_FORM) + [
        Paragraph("SOLICITUD DE LICENCIA MÉDICA", ESTILO_FORM_TITULO),
        Paragraph("Para el Personal", ESTILO_FORM_SUB),
    ] + parrafo_numero(numero) + [
        Spacer(1, 0.4 * cm),
        organismo, Spacer(1, 0.25 * cm),
        datos_agente, Spacer(1, 0.25 * cm),
        datos_pedido, Spacer(1, 0.25 * cm),
        tipo_tabla,
    ]
    if detalle:
        contenido += [Spacer(1, 0.25 * cm), _recuadro([Spacer(1, 0.1 * cm)] + detalle
                                                      + [Spacer(1, 0.1 * cm)])]
    contenido.append(_firmas())

    SimpleDocTemplate(ruta, pagesize=A4,
                      leftMargin=2 * cm, rightMargin=2 * cm,
                      topMargin=1.5 * cm, bottomMargin=1.5 * cm).build(contenido)


def _firmas():
    """Firma del agente y firma/sello de la autoridad."""
    estilo = ParagraphStyle("firma_sol", fontName="Helvetica", fontSize=9, leading=12,
                            alignment=TA_CENTER)
    tabla = Table([["", "", ""],
                   [Paragraph("Firma del agente", estilo), "",
                    Paragraph("Firma y sello de la autoridad", estilo)]],
                  colWidths=[6.5 * cm, 4 * cm, 6.5 * cm], rowHeights=[2.2 * cm, None])
    tabla.setStyle(TableStyle([
        ("LINEABOVE", (0, 1), (0, 1), 0.8, colors.black),
        ("LINEABOVE", (2, 1), (2, 1), 0.8, colors.black),
    ]))
    return KeepTogether([Spacer(1, 0.8 * cm), tabla])


def funcion_predeterminada(dni):
    """'Profesor/a - Sistemas Operativos, Nanotecnología' según sus materias vigentes."""
    materias = sorted({m for m, _c, est, *_ in designaciones_de(dni) if est.startswith("Vigente")})
    return "Profesor/a" + (f" - {', '.join(materias)}" if materias else "")


def ruta_certificado(dni, inicio, id_certificado):
    return str(carpeta_descargas() / f"certificado_medico_{dni}_{inicio:%Y%m%d}_{id_certificado}.pdf")


def vista_certificado_medico(page: ft.Page):

    # ---------- NUEVO CERTIFICADO ----------
    def abrir_formulario(d):
        ancho = 440
        hoy = date.today()
        fila_fecha, fecha_inicio = campo_fecha(
            page, "Fecha de inicio del reposo", valor=hoy.strftime(FORMATO), ancho=ancho,
            primera=date(hoy.year - 2, 1, 1), ultima=date(hoy.year + 1, 12, 31), inicial=hoy,
        )
        dias = ft.TextField(label="Cantidad de días de reposo", width=ancho,
                            keyboard_type=ft.KeyboardType.NUMBER,
                            input_filter=solo_numeros(), max_length=3)
        tipo_pedido = desplegable("Tipo de pedido", TIPOS_PEDIDO_MEDICO,
                                  valor=TIPOS_PEDIDO_MEDICO[0], ancho=ancho)
        parentesco = ft.TextField(label="Parentesco (solo para atención familiar)", width=ancho)
        funcion = ft.TextField(label="Función que cumple", width=ancho,
                               value=funcion_predeterminada(d[0]))
        horario = ft.TextField(label="Horario de trabajo (ej: Lunes a viernes de 19:30 a 22:30)",
                               width=ancho)
        medico = ft.TextField(label="Médico/a (opcional)", width=ancho)
        matricula = ft.TextField(label="Matrícula (opcional)", width=ancho)
        observaciones = ft.TextField(label="Observaciones (opcional)", width=ancho,
                                     multiline=True, min_lines=2, max_lines=4)
        error = ft.Text(color=ft.Colors.RED_700, visible=False)
        ocultar_error_al_escribir(page, error, dias, medico, matricula, observaciones,
                                  parentesco, funcion, horario)

        def mostrar_error(mensaje):
            error.value = mensaje
            error.visible = True
            page.update()

        def guardar(e):
            inicio = parse_fecha(fecha_inicio.value)
            if inicio is None:
                return mostrar_error("Elegí la fecha de inicio con el calendario.")
            if not dias.value.strip().isdigit() or int(dias.value) < 1:
                return mostrar_error("Los días deben ser un número mayor a 0.")
            if not tipo_pedido.value:
                return mostrar_error("Elegí el tipo de pedido.")
            if tipo_pedido.value == "Atención familiar" and not parentesco.value.strip():
                return mostrar_error("Indicá el parentesco del familiar.")
            if not funcion.value.strip():
                return mostrar_error("Indicá la función que cumple.")
            extra = (tipo_pedido.value, parentesco.value.strip(), funcion.value.strip(),
                     horario.value.strip())

            cantidad = int(dias.value)
            conexion = conectar()
            cursor = conexion.cursor()
            try:
                cursor.execute("SELECT id_docente FROM docentes WHERE dni = ?", (d[0],))
                id_docente = cursor.fetchone()[0]
                cursor.execute(
                    "INSERT INTO certificado_medico "
                    "(id_docente, fecha_emision, fecha_inicio, dias, medico, matricula, observaciones, "
                    "tipo_pedido, parentesco, funcion, horario) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (id_docente, date.today().strftime(FORMATO), inicio.strftime(FORMATO),
                     cantidad, medico.value.strip(), matricula.value.strip(),
                     observaciones.value.strip()) + extra,
                )
                id_certificado = cursor.lastrowid
                conexion.commit()
            except (sqlite3.Error, TypeError) as err:
                print("Error al guardar el certificado:", err)
                return mostrar_error("No se pudo guardar el certificado.")
            finally:
                cursor.close()
                conexion.close()

            cerrar_dialogo(page, dialogo)
            try:
                ruta = ruta_certificado(d[0], inicio, id_certificado)
                numero = emitir(
                    "Licencia médica", d, ruta,
                    lambda n: crear_certificado_medico(
                        d, inicio, cantidad, medico.value.strip(), matricula.value.strip(),
                        observaciones.value.strip(), ruta, tipo_pedido=extra[0],
                        parentesco=extra[1], funcion=extra[2], horario=extra[3], numero=n),
                    detalle=f"{extra[0]} - {cantidad} día(s) desde {inicio.strftime(FORMATO)}")
                conexion = conectar()
                try:
                    with conexion:
                        conexion.execute(
                            "UPDATE certificado_medico SET numero_constancia = ? "
                            "WHERE id_certificado = ?", (numero, id_certificado))
                finally:
                    conexion.close()
            except Exception as err:
                print("Error al generar el PDF:", err)
                return avisar(page, "Se guardó el certificado pero no se pudo generar el PDF. "
                                    "Podés reimprimirlo desde el historial.")

            avisar(page, f"Solicitud N° {numero} guardada en: {ruta}")
            abrir_archivo(ruta)

        controles = [
            ft.Text(f"{d[2]}, {d[1]} - DNI {d[0]}", weight=ft.FontWeight.BOLD),
            tipo_pedido, parentesco, funcion, horario,
            fila_fecha, dias, medico, matricula, observaciones, error,
        ]
        previos = certificados_de(d[0])[:5]
        if previos:
            controles.append(ft.Divider())
            controles.append(ft.Text("Certificados anteriores", weight=ft.FontWeight.BOLD))
            controles += [ft.Text(f"{c[2]} - {c[3]} día(s) - {c[7] or c[4] or ''}", size=13)
                          for c in previos]

        dialogo = None
        dialogo = ft.AlertDialog(
            modal=True,
            title=ft.Text("Solicitud de licencia médica"),
            content=ft.Column(controls=controles, tight=True,
                              scroll=ft.ScrollMode.AUTO, width=ancho + 20, spacing=12),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: cerrar_dialogo(page, dialogo)),
                ft.Button(content=ft.Text("Guardar y generar PDF"), icon=ft.Icons.PICTURE_AS_PDF,
                                  on_click=guardar),
            ],
        )
        page.show_dialog(dialogo)

    # ---------- HISTORIAL Y REIMPRESIÓN ----------
    def abrir_historial(d):
        estado = ft.Text(size=13, color=ft.Colors.GREY_700, selectable=True)
        tabla = ft.DataTable(
            columns=[
                ft.DataColumn(label=ft.Text("Emitido")),
                ft.DataColumn(label=ft.Text("Inicio")),
                ft.DataColumn(label=ft.Text("Hasta")),
                ft.DataColumn(label=ft.Text("Días")),
                ft.DataColumn(label=ft.Text("Tipo / Médico/a")),
                ft.DataColumn(label=ft.Text("Acciones")),
            ],
            rows=[],
        )
        sin_datos = ft.Text("Este docente no tiene certificados médicos registrados.",
                            color=ft.Colors.GREY_600, visible=False)

        def reimprimir(c):
            inicio = parse_fecha(c[2])
            if inicio is None:
                estado.value = "La fecha de inicio de este certificado no es válida."
                page.update()
                return
            try:
                ruta = ruta_certificado(d[0], inicio, c[0])
                crear_certificado_medico(d, inicio, c[3], c[4] or "", c[5] or "", c[6] or "", ruta,
                                         fecha_emision=parse_fecha(c[1]), tipo_pedido=c[7] or "",
                                         parentesco=c[8] or "", funcion=c[9] or "",
                                         horario=c[10] or "", numero=c[11])
            except PermissionError:
                estado.value = "No se pudo guardar: cerrá el PDF si lo tenés abierto."
                page.update()
                return
            except Exception as err:
                print("Error al reimprimir:", err)
                estado.value = "No se pudo generar el PDF."
                page.update()
                return
            estado.value = f"PDF guardado en: {ruta}"
            page.update()
            abrir_archivo(ruta)

        def pedir_borrado(c):
            def borrar():
                conexion = conectar()
                try:
                    with conexion:
                        conexion.execute(
                            "DELETE FROM certificado_medico WHERE id_certificado = ?", (c[0],))
                except sqlite3.Error as err:
                    print("Error al eliminar el certificado:", err)
                    avisar(page, "No se pudo eliminar el certificado.")
                    return
                finally:
                    conexion.close()
                abrir_historial(d)

            cerrar_dialogo(page, dialogo)
            confirmar(
                page, "Eliminar certificado",
                f"¿Eliminar el certificado del {c[2]} ({c[3]} día(s))? No se puede deshacer.",
                borrar, texto_boton="Eliminar", al_cancelar=lambda: abrir_historial(d))

        filas = []
        for c in certificados_de(d[0]):
            inicio = parse_fecha(c[2])
            hasta = (inicio + timedelta(days=c[3] - 1)).strftime(FORMATO) if inicio else "-"
            filas.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(c[1]))),
                ft.DataCell(ft.Text(str(c[2]))),
                ft.DataCell(ft.Text(hasta)),
                ft.DataCell(ft.Text(str(c[3]))),
                ft.DataCell(ft.Text(" / ".join(x for x in (c[7], c[4]) if x) or "-")),
                ft.DataCell(ft.Row(spacing=0, controls=[
                    ft.IconButton(icon=ft.Icons.PRINT, tooltip="Reimprimir PDF",
                                  on_click=lambda e, cert=c: reimprimir(cert)),
                    ft.IconButton(icon=ft.Icons.DELETE, tooltip="Eliminar",
                                  on_click=lambda e, cert=c: pedir_borrado(cert)),
                ])),
            ]))
        tabla.rows = filas
        tabla.visible = bool(filas)
        sin_datos.visible = not filas

        dialogo = None
        dialogo = ft.AlertDialog(
            title=ft.Text(f"Historial - {d[2]}, {d[1]}"),
            content=ft.Container(
                width=780, height=420,
                content=ft.Column(
                    controls=[ft.Row(controls=[tabla], scroll=ft.ScrollMode.AUTO), sin_datos, estado],
                    scroll=ft.ScrollMode.AUTO, spacing=12),
            ),
            actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(page, dialogo))],
        )
        page.show_dialog(dialogo)

    return vista_selector_docentes(
        page,
        titulo="Licencias médicas",
        subtitulo="Generá la solicitud de licencia médica o consultá el historial para reimprimir una anterior.",
        icono=ft.Icons.MEDICAL_SERVICES,
        texto_boton="Nueva solicitud",
        icono_boton=ft.Icons.NOTE_ADD,
        accion=abrir_formulario,
        color=ft.Colors.RED_700,
        acciones_extra=[(ft.Icons.HISTORY, "Historial y reimpresión", abrir_historial)],
    )
