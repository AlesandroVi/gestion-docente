"""Validación de los datos de un docente (la usan el registro y la edición)."""
import re
from datetime import date

from database.consultas import parse_fecha

RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PREFIJOS_CUIL = ("20", "23", "24", "27")
RE_NOMBRE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .-]*$")


def limites_nacimiento(hoy=None):
    """Rango del calendario: docentes de 18 a 100 años."""
    hoy = hoy or date.today()
    return date(hoy.year - 100, 1, 1), date(hoy.year - 18, hoy.month, min(hoy.day, 28))


def validar_docente(nombre, apellido, dni, cuil, fecha_nacimiento,
                    domicilio, email, caracter, caracteres_validos=None, hoy=None):
    """Devuelve (errores, datos). `errores` es {campo: mensaje}; `datos`, los valores limpios."""
    errores = {}
    nombre = " ".join((nombre or "").split())
    apellido = " ".join((apellido or "").split())
    dni = (dni or "").strip()
    cuil = (cuil or "").strip()
    domicilio = " ".join((domicilio or "").split())
    email = (email or "").strip().lower()
    fecha_nacimiento = (fecha_nacimiento or "").strip()
    caracter = (caracter or "").strip()

    if not nombre:
        errores["nombre"] = "Ingresá el nombre."
    elif not RE_NOMBRE.match(nombre):
        errores["nombre"] = "El nombre solo puede tener letras (sin números ni símbolos)."
    if not apellido:
        errores["apellido"] = "Ingresá el apellido."
    elif not RE_NOMBRE.match(apellido):
        errores["apellido"] = "El apellido solo puede tener letras (sin números ni símbolos)."

    if not dni:
        errores["dni"] = "Ingresá el DNI."
    elif not dni.isdigit():
        errores["dni"] = "El DNI debe tener solo números."
    elif not 7 <= len(dni) <= 8:
        errores["dni"] = "El DNI debe tener 7 u 8 números."

    if not cuil:
        errores["cuil"] = "Ingresá el CUIL."
    elif not cuil.isdigit():
        errores["cuil"] = "El CUIL debe tener solo números (sin guiones)."
    elif len(cuil) != 11:
        errores["cuil"] = "El CUIL debe tener 11 números."
    elif cuil[:2] not in PREFIJOS_CUIL:
        errores["cuil"] = "El CUIL debe empezar con 20, 23, 24 o 27."
    elif "dni" not in errores and cuil[2:10] != dni.zfill(8):
        errores["cuil"] = "El CUIL no coincide con el DNI (los 8 números del medio)."

    if not fecha_nacimiento:
        errores["fecha_nacimiento"] = "Elegí la fecha con el calendario."
    else:
        nacimiento = parse_fecha(fecha_nacimiento)
        primera, ultima = limites_nacimiento(hoy)
        if nacimiento is None:
            errores["fecha_nacimiento"] = "Elegí la fecha con el calendario."
        elif not primera <= nacimiento <= ultima:
            errores["fecha_nacimiento"] = "La fecha no es válida (el docente debe ser mayor de 18 años)."

    if not domicilio:
        errores["domicilio"] = "Ingresá el domicilio."

    if not email:
        errores["email"] = "Ingresá el email."
    elif not RE_EMAIL.match(email):
        errores["email"] = "El email no tiene un formato válido (ej: nombre@correo.com)."

    if not caracter:
        errores["caracter"] = "Elegí el carácter."
    elif caracteres_validos is not None and caracter not in caracteres_validos:
        errores["caracter"] = "Elegí una de las opciones de la lista."

    datos = {
        "nombre": nombre, "apellido": apellido, "dni": dni, "cuil": cuil,
        "fecha_nacimiento": fecha_nacimiento, "domicilio": domicilio,
        "email": email, "caracter": caracter,
    }
    return errores, datos


def campo_duplicado(error):
    """A partir de un sqlite3.IntegrityError, devuelve (campo, mensaje) o None."""
    texto = str(error).lower()
    if "unique" not in texto:
        return None
    if "docentes.dni" in texto:
        return "dni", "Ya existe un docente cargado con ese DNI."
    if "docentes.cuil" in texto:
        return "cuil", "Ya existe un docente cargado con ese CUIL."
    if "docentes.email" in texto:
        return "email", "Ya existe un docente cargado con ese email."
    return None


NOMBRES_CAMPOS = {
    "nombre": "Nombre", "apellido": "Apellido", "dni": "DNI", "cuil": "CUIL",
    "fecha_nacimiento": "Fecha de nacimiento", "domicilio": "Domicilio",
    "email": "Email", "caracter": "Carácter",
}
