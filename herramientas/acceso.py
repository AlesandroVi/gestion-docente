"""Pantalla de acceso con contraseña."""
import flet as ft

from config import LARGO_MINIMO_CLAVE
from database.seguridad import establecer_clave, hay_clave, verificar_clave


def pantalla_acceso(page: ft.Page, al_ingresar):
    """Muestra la pantalla de acceso. Si todavía no hay contraseña, pide crearla."""
    page.clean()
    primera_vez = not hay_clave()

    clave = ft.TextField(label="Contraseña", password=True, can_reveal_password=True,
                         width=340, autofocus=True)
    repetir = ft.TextField(label="Repetir contraseña", password=True, can_reveal_password=True,
                           width=340, visible=primera_vez)
    error = ft.Text(color=ft.Colors.RED_700, visible=False)

    def fallo(mensaje):
        error.value = mensaje
        error.visible = True
        page.update()

    def confirmar(e):
        if primera_vez:
            if len(clave.value or "") < LARGO_MINIMO_CLAVE:
                return fallo(f"La contraseña debe tener al menos {LARGO_MINIMO_CLAVE} caracteres.")
            if clave.value != repetir.value:
                return fallo("Las contraseñas no coinciden.")
            establecer_clave(clave.value)
        elif not verificar_clave(clave.value or ""):
            clave.value = ""
            return fallo("Contraseña incorrecta.")
        al_ingresar()

    clave.on_submit = repetir.on_submit = confirmar

    def ocultar(e):
        if error.visible:
            error.visible = False
            page.update()

    clave.on_change = repetir.on_change = ocultar

    titulo = "Creá una contraseña de acceso" if primera_vez else "Ingresá tu contraseña"
    detalle = ("Se te va a pedir cada vez que abras el sistema. Anotala en un lugar seguro."
               if primera_vez else "El sistema guarda datos personales del personal docente.")

    page.add(
        ft.Container(
            expand=True,
            alignment=ft.Alignment.CENTER,
            content=ft.Container(
                padding=35,
                border_radius=14,
                border=ft.Border.all(1, ft.Colors.GREY_300),
                content=ft.Column(
                    tight=True,
                    spacing=16,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.LOCK, size=48, color=ft.Colors.BLUE_700),
                        ft.Text("Sistema de Gestión Docente", size=22, weight=ft.FontWeight.BOLD),
                        ft.Text(titulo, size=16),
                        ft.Text(detalle, size=12, color=ft.Colors.GREY_600),
                        clave, repetir, error,
                        ft.Button(content=ft.Text("Crear y entrar" if primera_vez else "Entrar"),
                                          icon=ft.Icons.LOGIN, on_click=confirmar),
                    ],
                ),
            ),
        )
    )
