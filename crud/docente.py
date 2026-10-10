import sqlite3

import flet as ft

from config import CARACTERES
from crud.buscar import vista_buscar_docente
from crud.gestion import vista_gestion_docentes
from crud.validaciones import NOMBRES_CAMPOS, campo_duplicado, limites_nacimiento, validar_docente
from database.conexion import conectar
from ui import (
    abrir_archivo, autolimpiar, avisar, campo_fecha, carpeta_descargas, cerrar_dialogo,
    desplegable, mostrar_mensaje, poner_error, resumen_errores, solo_numeros,
)

ANCHO = 500


def vista_docentes(page: ft.Page):

    # ---------- CAMPOS DEL REGISTRO ----------
    nombre = ft.TextField(label="Nombre del docente", width=ANCHO)
    apellido = ft.TextField(label="Apellido del docente", width=ANCHO)
    dni = ft.TextField(label="DNI del docente (solo números)", width=ANCHO,
                       max_length=8, input_filter=solo_numeros(),
                       keyboard_type=ft.KeyboardType.NUMBER)
    cuil = ft.TextField(label="CUIL del docente (11 números, sin guiones)", width=ANCHO,
                        max_length=11, input_filter=solo_numeros(),
                        keyboard_type=ft.KeyboardType.NUMBER)
    primera, ultima = limites_nacimiento()
    fila_nacimiento, fecha_nacimiento = campo_fecha(
        page, "Fecha de nacimiento", ancho=ANCHO,
        primera=primera, ultima=ultima, inicial=ultima.replace(year=1985),
    )
    domicilio = ft.TextField(label="Domicilio del docente", width=ANCHO)
    email = ft.TextField(label="Email del docente", width=ANCHO,
                         keyboard_type=ft.KeyboardType.EMAIL)
    caracter = desplegable("Carácter del docente", CARACTERES, ancho=ANCHO)

    campos = {
        "nombre": nombre, "apellido": apellido, "dni": dni, "cuil": cuil,
        "fecha_nacimiento": fecha_nacimiento, "domicilio": domicilio,
        "email": email, "caracter": caracter,
    }

    autolimpiar(nombre, apellido, dni, cuil, domicilio, email)

    def limpiar():
        for campo in campos.values():
            campo.value = None if campo is caracter else ""
            poner_error(campo, None)
        page.update()

    def registrar_docente(e):
        errores, datos = validar_docente(
            nombre.value, apellido.value, dni.value, cuil.value,
            fecha_nacimiento.value, domicilio.value, email.value, caracter.value,
            caracteres_validos=CARACTERES,
        )
        for clave, campo in campos.items():
            poner_error(campo, errores.get(clave))
        if errores:
            page.update()
            avisar(page, resumen_errores(errores, NOMBRES_CAMPOS))
            return

        conexion = conectar()
        cursor = conexion.cursor()
        try:
            cursor.execute(
                "INSERT INTO docentes (nombre, apellido, dni, cuil, fecha_nacimiento, "
                "domicilio, email, caracter) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (datos["nombre"], datos["apellido"], datos["dni"], datos["cuil"],
                 datos["fecha_nacimiento"], datos["domicilio"], datos["email"],
                 datos["caracter"]),
            )
            conexion.commit()
        except sqlite3.IntegrityError as error:
            duplicado = campo_duplicado(error)
            if duplicado:
                poner_error(campos[duplicado[0]], duplicado[1])
                page.update()
                avisar(page, duplicado[1])
            else:
                print("Error al guardar el docente:", error)
                avisar(page, "No se pudo guardar el docente.")
            return
        except sqlite3.Error as error:
            print("Error al guardar el docente:", error)
            avisar(page, "No se pudo guardar el docente.")
            return
        finally:
            cursor.close()
            conexion.close()

        limpiar()
        recargar_gestion()
        recargar_busqueda()
        avisar(page, f"Docente {datos['apellido']}, {datos['nombre']} guardado correctamente.")

    boton_guardar_docente = ft.Button(content=ft.Text("Guardar docente"), icon=ft.Icons.SAVE, on_click=registrar_docente
    )
    boton_limpiar = ft.TextButton("Limpiar", on_click=lambda e: limpiar())

    # ---------- IMPORTAR DESDE EXCEL ----------
    def descargar_plantilla(e):
        from herramientas.importar import crear_plantilla
        ruta = carpeta_descargas() / "plantilla_docentes.xlsx"
        try:
            crear_plantilla(ruta)
        except PermissionError:
            return avisar(page, "No se pudo guardar: cerrá la plantilla si la tenés abierta.")
        avisar(page, f"Plantilla guardada en: {ruta}")
        abrir_archivo(ruta)

    async def importar_excel(e):
        from herramientas.importar import importar_docentes
        archivos = await ft.FilePicker().pick_files(
            dialog_title="Elegí la planilla de docentes", allowed_extensions=["xlsx"])
        if not archivos or not archivos[0].path:
            return
        try:
            importados, problemas = importar_docentes(archivos[0].path)
        except Exception as error:
            print("Error al importar:", error)
            return mostrar_mensaje(page, "No se pudo leer la planilla",
                                   "Revisá que sea un archivo de Excel (.xlsx) cerrado y con el "
                                   "formato de la plantilla.")
        recargar_gestion()
        recargar_busqueda()
        mostrar_resultado(importados, problemas)

    def mostrar_resultado(importados, problemas):
        controles = [ft.Row(spacing=10, controls=[
            ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_700),
            ft.Text(f"Se cargaron {importados} docente(s).", size=16, weight=ft.FontWeight.BOLD)])]
        if problemas:
            controles.append(ft.Text(f"{len(problemas)} fila(s) no se cargaron:",
                                     color=ft.Colors.RED_700, weight=ft.FontWeight.W_600))
            controles += [ft.Text(f"Fila {fila} - {nombre or 'sin nombre'}: {mensaje}", size=13,
                                  selectable=True)
                          for fila, nombre, mensaje in problemas]
            controles.append(ft.Text("Corregilas en el Excel y volvé a importarlo: las que ya "
                                     "se cargaron se saltean solas.", size=12,
                                     color=ft.Colors.GREY_700))
        dialogo = None
        dialogo = ft.AlertDialog(
            title=ft.Text("Resultado de la importación"),
            content=ft.Container(width=560, content=ft.Column(
                controls=controles, tight=True, spacing=8, scroll=ft.ScrollMode.AUTO)),
            actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(page, dialogo))],
        )
        page.show_dialog(dialogo)

    tarjeta_importar = ft.Container(
        width=ANCHO,
        padding=16,
        border_radius=12,
        border=ft.Border.all(1, ft.Colors.GREEN_700),
        bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.GREEN_700),
        content=ft.Column(spacing=10, controls=[
            ft.Row(spacing=10, controls=[
                ft.Icon(ft.Icons.UPLOAD_FILE, color=ft.Colors.GREEN_700),
                ft.Text("¿Tenés muchos docentes? Cargalos desde Excel", weight=ft.FontWeight.BOLD)]),
            ft.Text("1) Descargá la plantilla y completala.  2) Importala acá.", size=12,
                    color=ft.Colors.GREY_700),
            ft.Row(spacing=10, wrap=True, controls=[
                ft.OutlinedButton(content=ft.Text("Descargar plantilla"), icon=ft.Icons.DOWNLOAD,
                                  on_click=descargar_plantilla),
                ft.Button(content=ft.Text("Importar Excel"), icon=ft.Icons.UPLOAD,
                          on_click=importar_excel),
            ]),
        ]),
    )

    vista_registrar = ft.Column(
        controls=[
            ft.Text("Registro de Docente", size=30),
            nombre, apellido, dni, cuil,
            fila_nacimiento, domicilio, email, caracter,
            ft.Row(controls=[boton_guardar_docente, boton_limpiar],
                   alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(),
            tarjeta_importar,
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=15,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    vista_gestionar, recargar_gestion = vista_gestion_docentes(page)
    vista_buscar = vista_buscar_docente(page)
    recargar_busqueda = vista_buscar.data  # vuelve a leer la lista de la búsqueda

    return ft.Tabs(
        length=3,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(
                    tab_alignment=ft.TabAlignment.CENTER,
                    tabs=[ft.Tab(label="Registrar", icon=ft.Icons.PERSON_ADD),
                          ft.Tab(label="Gestionar", icon=ft.Icons.MANAGE_ACCOUNTS),
                          ft.Tab(label="Buscar docente", icon=ft.Icons.PERSON_SEARCH)],
                ),
                ft.TabBarView(expand=True, controls=[vista_registrar, vista_gestionar,
                                                             ft.Container(content=vista_buscar,
                                                                          padding=ft.Padding.only(top=16))]),
            ],
        ),
    )
