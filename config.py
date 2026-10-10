"""Configuración general del sistema.

Los datos de la institución (encabezado, firmante, localidad, horario de examen)
se editan desde la pantalla "Ajustes" y quedan guardados en la base de datos.
Acá solo están los valores iniciales, las rutas y algunas constantes.
"""
from pathlib import Path

# Todo se ubica SIEMPRE relativo a la carpeta del proyecto (donde está main.py),
# sin importar desde qué carpeta se ejecute el programa.
CARPETA_PROYECTO = Path(__file__).resolve().parent
RUTA_BD = CARPETA_PROYECTO / "Gestion.db"
CARPETA_COPIAS = CARPETA_PROYECTO / "copias_de_seguridad"

COPIAS_AUTOMATICAS_A_CONSERVAR = 15
CARACTERES = ["Interino", "Suplente"]
CARPETA_LOGOS = CARPETA_PROYECTO / "logos"

# Columnas de la constancia de trabajo: (código que se imprime, texto que se ve en la pantalla)
TURNOS = [("M", "Mañana"), ("T", "Tarde"), ("V", "Vespertino")]
SITUACIONES = [("I", "Interino"), ("S", "Suplente")]
CONDICIONES = [("1C", "1er cuatrimestre"), ("2C", "2do cuatrimestre"), ("A", "Anual")]
ANIOS = ["1°", "2°", "3°", "4°"]
TIPOS_DESIGNACION = ["Designación a término", "Concurso", "Suplencia"]
TIPOS_PEDIDO_MEDICO = ["Consultorio", "Domicilio", "Atención familiar"]
DIAS_AVISO_VENCIMIENTO = 30
LARGO_MINIMO_CLAVE = 6
TIPOS_LICENCIA = [
    "Licencia anual ordinaria",
    "Maternidad",
    "Paternidad",
    "Por estudio / examen",
    "Atención de familiar enfermo",
    "Razones particulares",
    "Sin goce de haberes",
    "Cargo de mayor jerarquía",
    "Otra",
]

# Valores iniciales de los datos de la institución (editables desde "Ajustes").
INSTITUCION_PREDETERMINADA = {
    "inst_encabezado": (
        "INSTITUTO DE CARRERAS\n"
        "SUPERIORES (I.C.S.) N° 6034\n"
        "EL GALPÓN (ANEXO 6021)"
    ),
    "inst_nombre": "Instituto de Carreras Superior N° 6.034",
    "firmante_nombre": "Prof. Nombre Apellido",
    "firmante_cargo": "Prosecretaria",
    "localidad": "El Galpón",
    "organismo": "MINISTERIO DE EDUCACION Y CULTURA DE SALTA",
    "dependencia": "I.C.S N° 6034 EL GALPON (ANEXO 6021)",
    "examen_hora_desde": "19:30",
    "examen_hora_hasta": "22:30",
}
