from datetime import datetime

import flet as ft
from database.conexion import inicializar_bd

inicializar_bd()

from database.consultas import FORMATO_FECHA, contar_docentes_activos  # noqa: E402
from herramientas.acceso import pantalla_acceso  # noqa: E402
from herramientas.avisos import (  # noqa: E402
    designaciones_por_vencer, licencias_vigentes, reposos_vigentes,
)
from herramientas.respaldo import copia_automatica  # noqa: E402

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

# Una copia automática por día, en la carpeta "copias_de_seguridad" del proyecto.
try:
    copia_automatica()
except Exception as error:
    print("No se pudo hacer la copia automática:", error)


def contar_docentes():
    """Cantidad de docentes activos (None si no se puede leer la BD)."""
    try:
        return contar_docentes_activos()
    except Exception:
        return None


def main(page: ft.Page):

    page.title = "Sistema de Gestión Docente"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE_700)

    # Calendarios en español (si esta versión no lo admite, se usa el idioma por defecto)
    try:
        page.locale_configuration = ft.LocaleConfiguration(
            supported_locales=[ft.Locale("es", "AR")],
            current_locale=ft.Locale("es", "AR"),
        )
    except Exception:
        pass

    def construir_app():
        page.clean()
        contenido = ft.Container(expand=True, padding=30)

        # -----------------------------------------
        # NAVEGACIÓN
        # índice 0 = Inicio (sin barra lateral)
        # -----------------------------------------

        def ir_a(indice):
            for i, elemento in items_menu.items():
                elemento.selected = i == indice
            # La barra lateral y su divisor solo aparecen fuera del inicio
            rail.visible = indice != 0
            divisor.visible = indice != 0
            cabecera_volver.visible = indice != 0
            contenido.content = VISTAS[indice]()
            page.update()

        def bloquear(e):
            pantalla_acceso(page, construir_app)

        # -----------------------------------------
        # VISTAS
        # -----------------------------------------

        def tarjeta(icono, titulo, descripcion, indice, color, al_tocar=None):
            def hover(e):
                activo = str(e.data).lower() == "true"
                e.control.bgcolor = ft.Colors.with_opacity(0.06, color) if activo else None
                e.control.border = ft.Border.all(2 if activo else 1, color if activo else ft.Colors.GREY_300)
                e.control.update()

            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Container(
                            content=ft.Icon(icono, size=36, color=ft.Colors.WHITE),
                            bgcolor=color,
                            width=64,
                            height=64,
                            border_radius=16,
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Text(titulo, size=19, weight=ft.FontWeight.BOLD),
                        ft.Text(descripcion, size=13, color=ft.Colors.GREY_700),
                    ],
                    spacing=10,
                ),
                width=280,
                height=190,
                padding=22,
                border_radius=14,
                border=ft.Border.all(1, ft.Colors.GREY_300),
                ink=True,
                on_click=al_tocar or (lambda e: ir_a(indice)),
                on_hover=hover,
            )

        def panel_avisos():
            """Reposos y licencias vigentes, materias sin cubrir y designaciones por vencer."""
            try:
                from herramientas.reportes import materias_sin_cubrir
                reposos = reposos_vigentes()
                licencias = licencias_vigentes()
                vencen = designaciones_por_vencer()
                vacantes, descubiertas = materias_sin_cubrir()
            except Exception as error:
                print("No se pudieron calcular los avisos:", error)
                return None

            lineas = []
            if reposos:
                lineas.append(ft.Text("Docentes con reposo médico vigente", weight=ft.FontWeight.BOLD))
                for nombre, dni, desde, hasta, faltan in reposos:
                    cuando = "termina hoy" if faltan == 0 else f"quedan {faltan} día(s)"
                    lineas.append(ft.Text(
                        f"• {nombre} (DNI {dni}): del {desde.strftime(FORMATO_FECHA)} al "
                        f"{hasta.strftime(FORMATO_FECHA)}, {cuando}", size=13))
            if licencias:
                lineas.append(ft.Text("Docentes de licencia", weight=ft.FontWeight.BOLD))
                for nombre, dni, tipo, desde, hasta, faltan in licencias:
                    cuando = "termina hoy" if faltan == 0 else f"quedan {faltan} día(s)"
                    lineas.append(ft.Text(
                        f"• {nombre} (DNI {dni}): {tipo}, del {desde.strftime(FORMATO_FECHA)} al "
                        f"{hasta.strftime(FORMATO_FECHA)}, {cuando}", size=13))
            if vacantes or descubiertas:
                lineas.append(ft.Text("Materias sin cubrir", weight=ft.FontWeight.BOLD))
                for m in descubiertas:
                    lineas.append(ft.Text(
                        f"• {m['materia']} ({m['carrera']}): docente ausente y sin suplente", size=13))
                if vacantes:
                    nombres = ", ".join(m["materia"] for m in vacantes[:5])
                    if len(vacantes) > 5:
                        nombres += f" y {len(vacantes) - 5} más"
                    lineas.append(ft.Text(
                        f"• {len(vacantes)} materia(s) sin docente designado: {nombres}", size=13))
                lineas.append(ft.TextButton(
                    "Ver en Carreras y designaciones → Reportes",
                    icon=ft.Icons.ARROW_FORWARD, on_click=lambda e: ir_a(2)))
            if vencen:
                lineas.append(ft.Text("Designaciones por vencer", weight=ft.FontWeight.BOLD))
                for nombre, materia, carrera, baja, faltan in vencen:
                    cuando = "vence hoy" if faltan == 0 else f"vence en {faltan} día(s)"
                    lineas.append(ft.Text(
                        f"• {nombre}: {materia} ({carrera}) - baja el "
                        f"{baja.strftime(FORMATO_FECHA)}, {cuando}", size=13))

            if not lineas:
                return ft.Container(
                    content=ft.Row(controls=[
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_700, size=24),
                        ft.Text("Sin avisos pendientes: no hay licencias, materias sin cubrir "
                                "ni designaciones por vencer.",
                                size=14),
                    ], spacing=10),
                    bgcolor=ft.Colors.GREEN_50,
                    padding=ft.Padding.symmetric(horizontal=18, vertical=12),
                    border_radius=10,
                )
            return ft.Container(
                content=ft.Column(
                    controls=[ft.Row(controls=[
                        ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE, color=ft.Colors.ORANGE_800, size=24),
                        ft.Text("Avisos", size=16, weight=ft.FontWeight.W_600),
                    ], spacing=10)] + lineas,
                    spacing=6,
                ),
                bgcolor=ft.Colors.ORANGE_50,
                padding=ft.Padding.symmetric(horizontal=18, vertical=12),
                border_radius=10,
            )

        def vista_inicio():
            ahora = datetime.now()
            fecha = f"{DIAS[ahora.weekday()].capitalize()} {ahora.day} de {MESES[ahora.month - 1]} de {ahora.year}"
            total = contar_docentes()

            resumen = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.GROUPS, color=ft.Colors.BLUE_700, size=28),
                        ft.Text(
                            f"{total} docente(s) activo(s) en el sistema"
                            if total is not None
                            else "Base de datos lista",
                            size=14,
                            weight=ft.FontWeight.W_500,
                        ),
                    ],
                    spacing=10,
                ),
                bgcolor=ft.Colors.BLUE_50,
                padding=ft.Padding.symmetric(horizontal=18, vertical=12),
                border_radius=10,
            )
            avisos = panel_avisos()

            # Al tocar "Constancias" se abre una ventana en el centro con las 3 opciones,
            # así se ven enseguida sin tener que bajar.
            def abrir_constancias(e):
                dialogo = None

                def elegir(indice):
                    dialogo.open = False
                    ir_a(indice)

                def opcion(icono, titulo, descripcion, indice, color):
                    return ft.Container(
                        content=ft.Row(spacing=16, controls=[
                            ft.Container(
                                content=ft.Icon(icono, size=30, color=ft.Colors.WHITE),
                                bgcolor=color, width=54, height=54, border_radius=12,
                                alignment=ft.Alignment.CENTER),
                            ft.Column(spacing=2, expand=True, controls=[
                                ft.Text(titulo, size=17, weight=ft.FontWeight.BOLD),
                                ft.Text(descripcion, size=13, color=ft.Colors.GREY_700),
                            ]),
                            ft.Icon(ft.Icons.CHEVRON_RIGHT, color=ft.Colors.GREY_500),
                        ]),
                        padding=14,
                        border_radius=12,
                        border=ft.Border.all(1, ft.Colors.GREY_300),
                        ink=True,
                        on_click=lambda e: elegir(indice),
                    )

                dialogo = ft.AlertDialog(
                    title=ft.Text("¿Qué constancia querés generar?"),
                    content=ft.Column(
                        tight=True, width=460, spacing=12,
                        controls=[
                            opcion(ft.Icons.WORK, "Constancia de trabajo",
                                   "Con la tabla de cátedras del docente.", 3, ft.Colors.TEAL_700),
                            opcion(ft.Icons.EVENT_NOTE, "Constancia de examen",
                                   "Mesa de examen: fecha y horario.", 4, ft.Colors.ORANGE_800),
                            opcion(ft.Icons.MEDICAL_SERVICES, "Licencia médica",
                                   "Solicitud de licencia médica para el personal.", 5,
                                   ft.Colors.RED_700),
                            ft.Divider(),
                            opcion(ft.Icons.MENU_BOOK, "Registro de constancias",
                                   "Las ya emitidas, con su número. Reimprimir una copia.", 7,
                                   ft.Colors.BLUE_GREY_700),
                        ],
                    ),
                    actions=[ft.TextButton("Cancelar",
                                           on_click=lambda e: cerrar_constancias(dialogo))],
                )
                page.show_dialog(dialogo)

            def cerrar_constancias(dialogo):
                dialogo.open = False
                page.update()

            return ft.Column(
                controls=[
                    ft.Text("Bienvenido", size=32, weight=ft.FontWeight.BOLD),
                    ft.Text(fecha, size=14, color=ft.Colors.GREY_600),
                    resumen,
                ] + ([avisos] if avisos is not None else []) + [
                    ft.Text("¿Qué querés hacer?", size=18, weight=ft.FontWeight.W_600),
                    ft.Row(
                        controls=[
                            tarjeta(
                                ft.Icons.PEOPLE,
                                "Docentes",
                                "Registrá, gestioná y buscá docentes (ficha completa con licencias).",
                                1,
                                ft.Colors.BLUE_700,
                            ),
                            tarjeta(
                                ft.Icons.MENU_BOOK,
                                "Carreras y designaciones",
                                "Cargá carreras, materias y designá docentes.",
                                2,
                                ft.Colors.PURPLE_700,
                            ),
                            tarjeta(
                                ft.Icons.DESCRIPTION,
                                "Constancias",
                                "Tocá para elegir: trabajo, examen o certificado médico.",
                                3,
                                ft.Colors.TEAL_700,
                                al_tocar=abrir_constancias,
                            ),
                            tarjeta(
                                ft.Icons.SETTINGS,
                                "Ajustes",
                                "Datos de la institución, copias de seguridad y contraseña.",
                                6,
                                ft.Colors.BLUE_GREY_700,
                            ),
                        ],
                        spacing=20,
                        run_spacing=20,
                        wrap=True,
                    ),
                ],
                spacing=14,
                scroll=ft.ScrollMode.AUTO,
            )

        def vista_docentes():
            from crud.docente import vista_docentes
            return vista_docentes(page)

        def vista_academica():
            from crud.academico import vista_academica
            return vista_academica(page)

        def vista_constancia_trabajo():
            from certificados.constanciaTrabajo import vista_constancia_trabajo
            return vista_constancia_trabajo(page)

        def vista_constancia_examen():
            # instalar si no están instalados: pip install flet reportlab openpyxl
            from certificados.mezaExamen import vista_mesas_examen
            return vista_mesas_examen(page)

        def vista_certificado_medico():
            from certificados.certificadoMedico import vista_certificado_medico
            return vista_certificado_medico(page)

        def vista_ajustes():
            from herramientas.ajustes import vista_ajustes
            return vista_ajustes(page)

        def vista_registro():
            from certificados.registro import vista_registro_constancias
            return vista_registro_constancias(page)

        VISTAS = [
            vista_inicio,
            vista_docentes,
            vista_academica,
            vista_constancia_trabajo,
            vista_constancia_examen,
            vista_certificado_medico,
            vista_ajustes,
            vista_registro,
        ]

        # -----------------------------------------
        # BARRA LATERAL (oculta en Inicio)
        # "Constancias" es una lista desplegable: al tocarla se ven Trabajo, Examen y Médico.
        # -----------------------------------------

        items_menu = {}

        def item(indice, icono, texto, sangria=False):
            elemento = ft.ListTile(
                leading=ft.Icon(icono),
                title=ft.Text(texto),
                dense=True,
                selected=False,
                on_click=lambda e, i=indice: ir_a(i),
            )
            items_menu[indice] = elemento
            if sangria:
                return ft.Container(content=elemento, padding=ft.Padding.symmetric(horizontal=18))
            return elemento

        constancias = ft.ExpansionTile(
            leading=ft.Icon(ft.Icons.DESCRIPTION),
            title=ft.Text("Constancias"),
            controls=[
                item(3, ft.Icons.WORK, "Trabajo", sangria=True),
                item(4, ft.Icons.EVENT_NOTE, "Examen", sangria=True),
                item(5, ft.Icons.MEDICAL_SERVICES, "Médico", sangria=True),
                item(7, ft.Icons.MENU_BOOK, "Registro", sangria=True),
            ],
        )

        rail = ft.Container(
            width=240,
            visible=False,
            padding=ft.Padding.symmetric(vertical=10),
            content=ft.Column(
                scroll=ft.ScrollMode.AUTO,
                spacing=2,
                controls=[
                    item(0, ft.Icons.HOME, "Inicio"),
                    item(1, ft.Icons.PEOPLE, "Docentes"),
                    item(2, ft.Icons.MENU_BOOK, "Carreras y designaciones"),
                    constancias,
                    item(6, ft.Icons.SETTINGS, "Ajustes"),
                ],
            ),
        )

        divisor = ft.VerticalDivider(width=1, visible=False)

        # -----------------------------------------
        # CABECERA
        # -----------------------------------------

        cabecera_volver = ft.TextButton(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.ARROW_BACK, color=ft.Colors.WHITE, size=18),
                    ft.Text("Inicio", color=ft.Colors.WHITE),
                ],
                spacing=6,
            ),
            visible=False,
            on_click=lambda e: ir_a(0),
        )

        cabecera = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.SCHOOL, color=ft.Colors.WHITE, size=30),
                    ft.Text(
                        "Sistema de Gestión Docente",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE,
                        expand=True,
                    ),
                    cabecera_volver,
                    ft.IconButton(
                        icon=ft.Icons.LOCK,
                        icon_color=ft.Colors.WHITE,
                        tooltip="Bloquear (volver a pedir la contraseña)",
                        on_click=bloquear,
                    ),
                ],
                spacing=12,
            ),
            bgcolor=ft.Colors.BLUE_700,
            padding=ft.Padding.symmetric(horizontal=25, vertical=14),
        )

        # -----------------------------------------
        # PANTALLA
        # -----------------------------------------

        contenido.content = vista_inicio()

        page.add(
            ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    cabecera,
                    ft.Row(
                        expand=True,
                        spacing=0,
                        controls=[
                            rail,
                            divisor,
                            contenido,
                        ],
                    ),
                ],
            )
        )

    # Primero se pide la contraseña (o se crea, la primera vez)
    pantalla_acceso(page, construir_app)


if __name__ == "__main__":
    ft.run(main)
