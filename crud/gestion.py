import sqlite3
from datetime import date

import flet as ft

from config import CARACTERES
from crud.validaciones import NOMBRES_CAMPOS, campo_duplicado, limites_nacimiento, validar_docente
from database.conexion import conectar
from database.consultas import certificados_de, designaciones_de, listar_docentes
from ui import (
    abrir_archivo, avisar, campo_fecha, carpeta_descargas, cerrar_dialogo,
    autolimpiar, confirmar, desplegable, mostrar_mensaje, poner_error, resumen_errores,
    solo_numeros,
)


def vista_gestion_docentes(page: ft.Page):
    """Devuelve (vista, recargar). `recargar()` vuelve a leer la tabla."""

    tabla = ft.DataTable(
        columns=[
            ft.DataColumn(label=ft.Text("DNI")),
            ft.DataColumn(label=ft.Text("Nombre")),
            ft.DataColumn(label=ft.Text("Apellido")),
            ft.DataColumn(label=ft.Text("CUIL")),
            ft.DataColumn(label=ft.Text("Nacimiento")),
            ft.DataColumn(label=ft.Text("Domicilio")),
            ft.DataColumn(label=ft.Text("Email")),
            ft.DataColumn(label=ft.Text("Carácter")),
            ft.DataColumn(label=ft.Text("Estado")),
            ft.DataColumn(label=ft.Text("Acciones")),
        ],
        rows=[],
    )
    contador = ft.Text(size=13, color=ft.Colors.GREY_600)

    # ---------- BUSCADOR (arriba) ----------
    buscador = ft.TextField(
        label="Buscar por DNI, nombre o apellido",
        prefix_icon=ft.Icons.SEARCH,
        width=400,
        on_change=lambda e: cargar_tabla(),
    )
    ver_inactivos = ft.Switch(
        label="Mostrar inactivos", value=False, on_change=lambda e: cargar_tabla()
    )

    # ---------- CARGAR TABLA ----------
    def cargar_tabla(filtro=None):
        if filtro is None:
            filtro = buscador.value or ""
        docentes = listar_docentes(filtro, incluir_inactivos=bool(ver_inactivos.value))

        filas = []
        for d in docentes:
            activo = bool(d[8])
            gris = None if activo else ft.Colors.GREY_500
            celdas = [ft.DataCell(ft.Text(str(valor), color=gris)) for valor in d[:8]]
            celdas.append(ft.DataCell(ft.Text(
                "Activo" if activo else "Inactivo",
                color=ft.Colors.GREEN_700 if activo else ft.Colors.GREY_500,
                weight=ft.FontWeight.W_500,
            )))

            botones = [
                ft.IconButton(icon=ft.Icons.VISIBILITY, tooltip="Ver información",
                              on_click=lambda e, doc=d: ver_informacion(doc)),
                ft.IconButton(icon=ft.Icons.EDIT, tooltip="Modificar",
                              on_click=lambda e, doc=d: abrir_edicion(doc)),
            ]
            if activo:
                botones.append(ft.IconButton(
                    icon=ft.Icons.PERSON_OFF,
                    tooltip="Dar de baja (pasa a inactivo, se conserva el historial)",
                    on_click=lambda e, doc=d: confirmar_baja(doc)))
            else:
                botones.append(ft.IconButton(
                    icon=ft.Icons.RESTORE, tooltip="Reactivar",
                    on_click=lambda e, doc=d: reactivar(doc)))
                botones.append(ft.IconButton(
                    icon=ft.Icons.DELETE_FOREVER, icon_color=ft.Colors.RED_700,
                    tooltip="Eliminar definitivamente",
                    on_click=lambda e, doc=d: eliminar_definitivo(doc)))
            celdas.append(ft.DataCell(ft.Row(controls=botones, spacing=0)))
            filas.append(ft.DataRow(cells=celdas))

        tabla.rows = filas
        contador.value = f"{len(filas)} docente(s)"
        page.update()

    # ---------- VER INFORMACIÓN ----------
    def ver_informacion(d):
        designaciones = designaciones_de(d[0])
        certificados = certificados_de(d[0])

        def fila(etiqueta, valor):
            return ft.Row(
                controls=[
                    ft.Text(etiqueta, weight=ft.FontWeight.BOLD, width=150),
                    ft.Text(str(valor), selectable=True, expand=True),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            )

        def seccion(titulo):
            return ft.Text(titulo, size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)

        controles = [
            seccion("Datos personales"),
            fila("Apellido y nombre", f"{d[2]}, {d[1]}"),
            fila("DNI", d[0]),
            fila("CUIL", d[3]),
            fila("Nacimiento", d[4]),
            fila("Domicilio", d[5]),
            fila("Email", d[6]),
            fila("Carácter", d[7]),
            fila("Estado", "Activo" if d[8] else "Inactivo"),
            ft.Divider(),
        ]

        lineas_des = []
        for mat, car, est, alta, baja, _disp in designaciones:
            texto = f"{mat} ({car}) - {est}. Alta: {alta}"
            if baja:
                texto += f" - Baja: {baja}"
            lineas_des.append(ft.Text(texto))
        if not lineas_des:
            lineas_des.append(ft.Text("Sin designaciones cargadas.", color=ft.Colors.GREY_600))
        controles.append(ft.ExpansionTile(
            leading=ft.Icon(ft.Icons.ASSIGNMENT_IND, color=ft.Colors.PURPLE_700),
            title=ft.Text(f"Designaciones ({len(designaciones)})", weight=ft.FontWeight.BOLD),
            controls=lineas_des,
        ))

        lineas_cert = [ft.Text(f"{c[2]} - {c[3]} día(s) - {c[4] or 'sin médico'}")
                       for c in certificados]
        if not lineas_cert:
            lineas_cert.append(ft.Text("Sin certificados médicos registrados.", color=ft.Colors.GREY_600))
        controles.append(ft.ExpansionTile(
            leading=ft.Icon(ft.Icons.MEDICAL_SERVICES, color=ft.Colors.RED_700),
            title=ft.Text(f"Certificados médicos ({len(certificados)})", weight=ft.FontWeight.BOLD),
            controls=lineas_cert,
        ))

        dialogo = None
        dialogo = ft.AlertDialog(
            title=ft.Text("Información del docente"),
            content=ft.Container(
                width=560,
                height=460,
                content=ft.Column(controls=controles, scroll=ft.ScrollMode.AUTO, spacing=8),
            ),
            actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(page, dialogo))],
        )
        page.show_dialog(dialogo)

    # ---------- MODIFICAR ----------
    def abrir_edicion(d):
        ancho = 420
        dni = ft.TextField(label="DNI", value=str(d[0]), read_only=True, width=ancho)
        nombre = ft.TextField(label="Nombre", value=d[1], width=ancho)
        apellido = ft.TextField(label="Apellido", value=d[2], width=ancho)
        cuil = ft.TextField(label="CUIL (11 números)", value=str(d[3]), width=ancho,
                            max_length=11, input_filter=solo_numeros())
        primera, ultima = limites_nacimiento()
        fila_nacimiento, fecha_nacimiento = campo_fecha(
            page, "Fecha de nacimiento", valor=d[4], ancho=ancho,
            primera=primera, ultima=ultima, inicial=ultima.replace(year=1985),
        )
        domicilio = ft.TextField(label="Domicilio", value=d[5], width=ancho)
        email = ft.TextField(label="Email", value=d[6], width=ancho)

        opciones = list(CARACTERES)
        if d[7] and d[7] not in opciones:  # valor viejo escrito a mano: se conserva
            opciones.append(d[7])
        caracter = desplegable("Carácter", opciones, valor=d[7], ancho=ancho)

        campos = {
            "cuil": cuil, "nombre": nombre, "apellido": apellido,
            "fecha_nacimiento": fecha_nacimiento, "domicilio": domicilio,
            "email": email, "caracter": caracter,
        }

        autolimpiar(nombre, apellido, cuil, domicilio, email)
        resumen = ft.Text(color=ft.Colors.RED_700, visible=False)

        def guardar(e):
            errores, datos = validar_docente(
                nombre.value, apellido.value, dni.value, cuil.value,
                fecha_nacimiento.value, domicilio.value, email.value, caracter.value,
                caracteres_validos=opciones,
            )
            for clave, campo in campos.items():
                poner_error(campo, errores.get(clave))
            resumen.visible = bool(errores)
            if errores:
                resumen.value = resumen_errores(errores, NOMBRES_CAMPOS)
                page.update()
                return

            conexion = conectar()
            cursor = conexion.cursor()
            try:
                cursor.execute(
                    "UPDATE docentes SET nombre = ?, apellido = ?, cuil = ?, fecha_nacimiento = ?, "
                    "domicilio = ?, email = ?, caracter = ? WHERE dni = ?",
                    (datos["nombre"], datos["apellido"], datos["cuil"], datos["fecha_nacimiento"],
                     datos["domicilio"], datos["email"], datos["caracter"], dni.value),
                )
                conexion.commit()
            except sqlite3.IntegrityError as error:
                duplicado = campo_duplicado(error)
                if duplicado:
                    poner_error(campos[duplicado[0]], duplicado[1])
                else:
                    print("Error al modificar el docente:", error)
                    poner_error(cuil, "No se pudo guardar. Revisá los datos.")
                page.update()
                return
            except sqlite3.Error as error:
                print("Error al modificar el docente:", error)
                poner_error(cuil, "No se pudo guardar. Revisá los datos.")
                page.update()
                return
            finally:
                cursor.close()
                conexion.close()

            cerrar_dialogo(page, dialogo)
            cargar_tabla()
            avisar(page, "Docente modificado correctamente.")

        dialogo = None
        dialogo = ft.AlertDialog(
            modal=True,
            title=ft.Text("Modificar docente"),
            content=ft.Column(
                controls=[dni, nombre, apellido, cuil, fila_nacimiento, domicilio, email, caracter, resumen],
                tight=True,
                scroll=ft.ScrollMode.AUTO,
                width=ancho + 20,
                spacing=12,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: cerrar_dialogo(page, dialogo)),
                ft.Button(content=ft.Text("Guardar"), on_click=guardar),
            ],
        )
        page.show_dialog(dialogo)

    # ---------- DAR DE BAJA / REACTIVAR / ELIMINAR ----------
    def _cambiar_activo(dni, valor):
        conexion = conectar()
        try:
            with conexion:
                conexion.execute("UPDATE docentes SET activo = ? WHERE dni = ?", (valor, dni))
            return True
        except sqlite3.Error as error:
            print("Error al cambiar el estado del docente:", error)
            return False
        finally:
            conexion.close()

    def confirmar_baja(d):
        def dar_de_baja():
            if _cambiar_activo(d[0], 0):
                cargar_tabla()
                avisar(page, f"{d[2]}, {d[1]} pasó a inactivo. Su historial se conserva.")
            else:
                avisar(page, "No se pudo dar de baja al docente.")

        confirmar(
            page,
            "Dar de baja al docente",
            f"{d[2]}, {d[1]} pasará a inactivo: dejará de aparecer en las listas para "
            "generar certificados, pero se conservan sus designaciones y certificados. "
            "Podés reactivarlo cuando quieras.",
            dar_de_baja,
            texto_boton="Dar de baja",
        )

    def reactivar(d):
        if _cambiar_activo(d[0], 1):
            cargar_tabla()
            avisar(page, f"{d[2]}, {d[1]} fue reactivado.")
        else:
            avisar(page, "No se pudo reactivar al docente.")

    def eliminar_definitivo(d):
        conexion = conectar()
        try:
            n_designaciones = conexion.execute(
                "SELECT COUNT(*) FROM designacion de JOIN docentes doc "
                "ON doc.id_docente = de.id_docente WHERE doc.dni = ?", (d[0],)).fetchone()[0]
        finally:
            conexion.close()
        n_certificados = len(certificados_de(d[0]))

        if n_designaciones:
            mostrar_mensaje(
                page, "No se puede eliminar",
                f"{d[2]}, {d[1]} tiene {n_designaciones} designación(es) registrada(s). "
                "Para no perder el historial, dejalo como inactivo.")
            return

        def borrar():
            conexion = conectar()
            try:
                with conexion:
                    conexion.execute("DELETE FROM docentes WHERE dni = ?", (d[0],))
            except sqlite3.Error as error:
                print("Error al eliminar el docente:", error)
                avisar(page, "No se pudo eliminar al docente.")
                return
            finally:
                conexion.close()
            cargar_tabla()
            avisar(page, "Docente eliminado definitivamente.")

        aviso_cert = (f" También se borrarán sus {n_certificados} certificado(s) médico(s)."
                      if n_certificados else "")
        confirmar(
            page, "Eliminar definitivamente",
            f"¿Seguro que querés eliminar a {d[1]} {d[2]}? Esta acción no se puede deshacer."
            + aviso_cert,
            borrar, texto_boton="Eliminar",
        )

    # ---------- EXPORTAR A EXCEL ----------
    def exportar(e):
        try:
            from herramientas.exportar import exportar_docentes_excel
        except ImportError:
            avisar(page, "Falta instalar openpyxl:  pip install openpyxl")
            return
        try:
            ruta = str(carpeta_descargas() / f"docentes_{date.today():%Y%m%d}.xlsx")
            exportar_docentes_excel(ruta)
        except PermissionError:
            avisar(page, "No se pudo guardar: cerrá el archivo Excel si lo tenés abierto.")
            return
        except Exception as error:
            print("Error al exportar a Excel:", error)
            avisar(page, "No se pudo exportar el listado.")
            return
        avisar(page, f"Listado guardado en: {ruta}")
        abrir_archivo(ruta)

    cargar_tabla()

    vista = ft.Column(
        controls=[
            ft.Text("Gestionar Docentes", size=30),
            ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    buscador,
                    ft.IconButton(
                        icon=ft.Icons.REFRESH,
                        tooltip="Actualizar tabla",
                        on_click=lambda e: cargar_tabla(),
                    ),
                    ver_inactivos,
                    ft.Button(content=ft.Text("Exportar a Excel"), icon=ft.Icons.TABLE_VIEW, on_click=exportar),
                ],
            ),
            contador,
            ft.Row(
                controls=[tabla],
                alignment=ft.MainAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO),
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=15,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
    return vista, cargar_tabla
