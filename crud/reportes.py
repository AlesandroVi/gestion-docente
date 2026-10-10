"""Pestaña Reportes: materias sin cubrir y planta docente por carrera."""
import flet as ft

from crud.academico import _columna, _consultar, _lista
from herramientas.reportes import exportar_planta_excel, exportar_planta_pdf, materias_sin_cubrir
from ui import abrir_archivo, actualizar_opciones, avisar, carpeta_descargas, desplegable

COLOR = ft.Colors.BLUE_700


def _fila(item, icono, color):
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=14, vertical=8),
        border_radius=10,
        bgcolor=ft.Colors.with_opacity(0.05, color),
        content=ft.Row(vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
            ft.Icon(icono, color=color),
            ft.Column(expand=True, spacing=2, controls=[
                ft.Text(f"{item['materia']}  ({item['horas']} hs)", weight=ft.FontWeight.BOLD),
                ft.Text(f"{item['carrera']}  ·  {item['detalle']}", size=12,
                        color=ft.Colors.GREY_700),
            ]),
        ]),
    )


def tab_reportes(page, refrescar_todo, registrar):
    resumen = ft.Row(spacing=14, wrap=True)
    lista_vacantes = ft.Column(spacing=6)
    lista_descubiertas = ft.Column(spacing=6)
    carrera = desplegable("Carrera", [], ancho=420)

    def tarjeta_numero(cantidad, texto, color, icono):
        return ft.Container(
            width=260, padding=16, border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.08, color),
            content=ft.Row(spacing=14, controls=[
                ft.Icon(icono, color=color, size=34),
                ft.Column(spacing=0, controls=[
                    ft.Text(str(cantidad), size=26, weight=ft.FontWeight.BOLD, color=color),
                    ft.Text(texto, size=13),
                ]),
            ]),
        )

    def cargar():
        vacantes, descubiertas = materias_sin_cubrir()
        resumen.controls = [
            tarjeta_numero(len(vacantes), "materia(s) sin docente", ft.Colors.RED_700,
                           ft.Icons.EVENT_SEAT),
            tarjeta_numero(len(descubiertas), "con el docente ausente\ny sin suplente",
                           ft.Colors.ORANGE_800, ft.Icons.PERSON_OFF),
        ]
        lista_vacantes.controls = [_fila(v, ft.Icons.EVENT_SEAT, ft.Colors.RED_700)
                                   for v in vacantes] or [
            ft.Text("Todas las materias tienen docente designado.", color=ft.Colors.GREEN_700)]
        lista_descubiertas.controls = [_fila(v, ft.Icons.PERSON_OFF, ft.Colors.ORANGE_800)
                                       for v in descubiertas] or [
            ft.Text("No hay materias sin cubrir por licencias.", color=ft.Colors.GREEN_700)]

        carreras = [("0", "Todas las carreras")] + [
            (f[0], f[1]) for f in _consultar("SELECT id_carrera, nom_carrera FROM carrera "
                                             "ORDER BY nom_carrera")]
        ids = {str(c[0]) for c in carreras}
        actualizar_opciones(carrera, carreras, carrera.value if carrera.value in ids else "0")

    def recargar():
        cargar()
        page.update()

    def exportar(formato):
        id_carrera = int(carrera.value) if carrera.value and carrera.value != "0" else None
        ruta = carpeta_descargas() / f"planta_docente.{formato}"
        try:
            if formato == "pdf":
                exportar_planta_pdf(str(ruta), id_carrera)
            else:
                exportar_planta_excel(str(ruta), id_carrera)
        except PermissionError:
            return avisar(page, "No se pudo guardar: cerrá el archivo si lo tenés abierto.")
        except Exception as error:
            print("Error al exportar la planta docente:", error)
            return avisar(page, "No se pudo generar la planta docente.")
        avisar(page, f"Planta docente guardada en: {ruta}")
        abrir_archivo(ruta)

    registrar(recargar)
    cargar()
    return _columna([
        _lista("Materias sin cubrir", ft.Icons.WARNING_AMBER, ft.Colors.RED_700, [
            resumen,
            ft.Text("Sin docente designado", size=15, weight=ft.FontWeight.W_600),
            lista_vacantes,
            ft.Text("Docente de licencia o con carpeta médica, sin suplente",
                    size=15, weight=ft.FontWeight.W_600),
            ft.Text("Cargá un suplente en la pestaña «Suplencias» para cubrirlas.",
                    size=12, color=ft.Colors.GREY_600),
            lista_descubiertas,
        ]),
        _lista("Planta docente", ft.Icons.TABLE_VIEW, COLOR, [
            ft.Text("Listado por carrera con cada materia, su docente, horas y situación de hoy "
                    "(las vacantes y los docentes ausentes salen marcados en rojo).",
                    size=13, color=ft.Colors.GREY_700),
            ft.Row(wrap=True, spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                   controls=[
                       carrera,
                       ft.Button(content=ft.Text("Generar PDF"), icon=ft.Icons.PICTURE_AS_PDF,
                                 on_click=lambda e: exportar("pdf")),
                       ft.Button(content=ft.Text("Exportar a Excel"), icon=ft.Icons.TABLE_VIEW,
                                 on_click=lambda e: exportar("xlsx")),
                   ]),
        ]),
    ])
