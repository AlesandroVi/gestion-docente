"""Pantalla de ajustes: datos de la institución, copias de seguridad y contraseña."""
from pathlib import Path

import flet as ft

from config import CARPETA_COPIAS, LARGO_MINIMO_CLAVE
from database import ajustes
from database.seguridad import establecer_clave, verificar_clave
from herramientas.respaldo import hacer_copia, listar_copias
from ui import avisar, confirmar, mostrar_mensaje, obtener_error, poner_error

ANCHO = 560


def _columna(controles):
    return ft.Column(controls=controles, scroll=ft.ScrollMode.AUTO, spacing=15,
                     horizontal_alignment=ft.CrossAxisAlignment.CENTER)


# ---------- DATOS DE LA INSTITUCIÓN ----------

def _tab_institucion(page):
    cfg = ajustes.institucion()
    encabezado = ft.TextField(label="Encabezado de los certificados (una línea por renglón)",
                              value=cfg["inst_encabezado"], multiline=True, min_lines=3, max_lines=5,
                              width=ANCHO)
    nombre = ft.TextField(label="Nombre completo de la institución", value=cfg["inst_nombre"], width=ANCHO)
    firmante = ft.TextField(label="Nombre de quien firma (ej: Profesora Apellido Nombre)",
                            value=cfg["firmante_nombre"], width=ANCHO)
    cargo = ft.TextField(label="Cargo de quien firma", value=cfg["firmante_cargo"], width=ANCHO)
    localidad = ft.TextField(label="Localidad", value=cfg["localidad"], width=ANCHO)
    organismo = ft.TextField(label="Organismo (solicitud de licencia médica)",
                             value=cfg["organismo"], width=ANCHO)
    dependencia = ft.TextField(label="Dependencia (solicitud de licencia médica)",
                               value=cfg["dependencia"], width=ANCHO)
    desde = ft.TextField(label="Horario de examen: inicio habitual (hh:mm)",
                         value=cfg["examen_hora_desde"], width=ANCHO // 2 - 6)
    hasta = ft.TextField(label="Horario de examen: fin habitual (hh:mm)",
                         value=cfg["examen_hora_hasta"], width=ANCHO // 2 - 6)
    campos = {"inst_encabezado": encabezado, "inst_nombre": nombre, "firmante_nombre": firmante,
              "firmante_cargo": cargo, "localidad": localidad,
              "organismo": organismo, "dependencia": dependencia,
              "examen_hora_desde": desde, "examen_hora_hasta": hasta}

    def guardar(e):
        from certificados.mezaExamen import normalizar_hora
        vacios = [c for c in (encabezado, nombre, firmante, cargo, localidad, organismo, dependencia) if not (c.value or "").strip()]
        h1, h2 = normalizar_hora(desde.value), normalizar_hora(hasta.value)
        for campo in campos.values():
            poner_error(campo, None)
        for campo in vacios:
            poner_error(campo, "Este dato es obligatorio.")
        if not h1:
            poner_error(desde, "Usá el formato hh:mm.")
        if not h2:
            poner_error(hasta, "Usá el formato hh:mm.")
        if vacios or not h1 or not h2:
            page.update()
            return
        valores = {k: (c.value or "").strip() for k, c in campos.items()}
        valores["examen_hora_desde"], valores["examen_hora_hasta"] = h1, h2
        ajustes.guardar_varios(valores)
        page.update()
        avisar(page, "Datos de la institución guardados. Se usan en todos los certificados nuevos.")

    def restaurar():
        ajustes.restaurar_institucion()
        valores = ajustes.institucion()
        for clave, campo in campos.items():
            campo.value = valores[clave]
            poner_error(campo, None)
        page.update()
        avisar(page, "Se restauraron los datos originales.")

    return _columna([
        ft.Text("Datos de la institución", size=30),
        ft.Text("Se usan en el encabezado, el texto y la firma de todos los PDF.",
                color=ft.Colors.GREY_600),
        encabezado, nombre, firmante, cargo, localidad, organismo, dependencia,
        ft.Text("Logos: poné los archivos logo_izquierdo.png, logo_centro.png y logo_derecho.png "
                "en la carpeta «logos» del proyecto.", size=12, color=ft.Colors.GREY_600),
        ft.Row(controls=[desde, hasta], alignment=ft.MainAxisAlignment.CENTER, spacing=12),
        ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[
            ft.Button(content=ft.Text("Guardar"), icon=ft.Icons.SAVE, on_click=guardar),
            ft.TextButton("Restaurar valores originales",
                          on_click=lambda e: confirmar(page, "Restaurar valores",
                                                       "Se vuelven a los datos con los que venía el sistema.",
                                                       restaurar, texto_boton="Restaurar")),
        ]),
    ])


# ---------- COPIAS DE SEGURIDAD ----------

def _tab_copias(page):
    carpeta = ft.TextField(
        label="Carpeta de destino (pendrive o carpeta sincronizada con la nube)",
        value=ajustes.obtener("carpeta_copia", ""), width=ANCHO)
    estado = ft.Text(selectable=True)
    automaticas = ft.Text(size=13, color=ft.Colors.GREY_700)

    def refrescar_automaticas():
        copias = listar_copias()
        automaticas.value = (
            f"Copias automáticas guardadas en: {CARPETA_COPIAS}\n"
            f"Hay {len(copias)} copia(s); la última es del "
            f"{copias[0].stem.replace('Auto_', '').replace('_', ' ')}." if copias else
            f"Copias automáticas en: {CARPETA_COPIAS} (todavía no hay ninguna).")

    async def elegir(e):
        try:
            ruta = await ft.FilePicker().get_directory_path(dialog_title="Elegí la carpeta de destino")
        except Exception as error:
            print("No se pudo abrir el selector de carpetas:", error)
            avisar(page, "No se pudo abrir el selector. Escribí la ruta a mano en el campo.")
            return
        if ruta:
            carpeta.value = ruta
            page.update()

    def copiar(e):
        destino = (carpeta.value or "").strip()
        if not destino:
            estado.value = "Elegí o escribí la carpeta de destino."
            estado.color = ft.Colors.RED_700
            page.update()
            return
        try:
            ruta = hacer_copia(Path(destino))
        except Exception as error:
            print("Error al hacer la copia:", error)
            estado.value = f"No se pudo hacer la copia: {error}"
            estado.color = ft.Colors.RED_700
            page.update()
            return
        ajustes.guardar("carpeta_copia", destino)
        estado.value = f"Copia guardada correctamente en: {ruta}"
        estado.color = ft.Colors.GREEN_700
        page.update()

    refrescar_automaticas()
    return _columna([
        ft.Text("Copias de seguridad", size=30),
        ft.Text("Todos los datos están en un único archivo (Gestion.db). Hacé copias seguido y "
                "guardalas fuera de esta computadora: en un pendrive o en una carpeta de Google "
                "Drive / OneDrive.", color=ft.Colors.GREY_600, width=ANCHO),
        ft.Row(controls=[carpeta, ft.IconButton(icon=ft.Icons.FOLDER_OPEN, tooltip="Elegir carpeta",
                                                on_click=elegir)],
               alignment=ft.MainAxisAlignment.CENTER),
        ft.Button(content=ft.Text("Hacer copia de seguridad"), icon=ft.Icons.BACKUP, on_click=copiar),
        estado,
        ft.Divider(),
        automaticas,
        ft.Text("Para recuperar una copia: cerrá el sistema y reemplazá Gestion.db (en la carpeta del "
                "programa) por la copia, renombrándola como Gestion.db.",
                size=12, color=ft.Colors.GREY_600, width=ANCHO),
    ])


# ---------- SEGURIDAD ----------

def _tab_seguridad(page):
    actual = ft.TextField(label="Contraseña actual", password=True, can_reveal_password=True, width=360)
    nueva = ft.TextField(label="Contraseña nueva", password=True, can_reveal_password=True, width=360)
    repetir = ft.TextField(label="Repetir contraseña nueva", password=True, can_reveal_password=True,
                           width=360)

    def cambiar(e):
        for campo in (actual, nueva, repetir):
            poner_error(campo, None)
        if not verificar_clave(actual.value or ""):
            poner_error(actual, "La contraseña actual no es correcta.")
        if len(nueva.value or "") < LARGO_MINIMO_CLAVE:
            poner_error(nueva, f"Debe tener al menos {LARGO_MINIMO_CLAVE} caracteres.")
        elif nueva.value != repetir.value:
            poner_error(repetir, "Las contraseñas no coinciden.")
        if obtener_error(actual) or obtener_error(nueva) or obtener_error(repetir):
            page.update()
            return
        establecer_clave(nueva.value)
        for campo in (actual, nueva, repetir):
            campo.value = ""
        page.update()
        avisar(page, "Contraseña cambiada correctamente.")

    return _columna([
        ft.Text("Seguridad", size=30),
        ft.Text("Cambiar la contraseña de acceso al sistema.", color=ft.Colors.GREY_600),
        actual, nueva, repetir,
        ft.Button(content=ft.Text("Cambiar contraseña"), icon=ft.Icons.KEY, on_click=cambiar),
        ft.Text("La contraseña impide abrir el programa, pero el archivo Gestion.db no está cifrado: "
                "cuidá también quién tiene acceso a la computadora y a las copias de seguridad.",
                size=12, color=ft.Colors.GREY_600, width=ANCHO),
    ])


def vista_ajustes(page: ft.Page):
    return ft.Tabs(
        length=3,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(
                    tab_alignment=ft.TabAlignment.CENTER,
                    tabs=[ft.Tab(label="Institución"), ft.Tab(label="Copias de seguridad"),
                          ft.Tab(label="Seguridad")],
                ),
                ft.TabBarView(expand=True, controls=[
                    _tab_institucion(page), _tab_copias(page), _tab_seguridad(page)]),
            ],
        ),
    )
