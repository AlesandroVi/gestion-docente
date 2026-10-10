"""Pruebas de crud/validaciones.py. Ejecutar desde la carpeta del proyecto:
    python -m unittest discover tests
"""
import sqlite3
import unittest
from datetime import date

from crud.validaciones import campo_duplicado, limites_nacimiento, validar_docente

HOY = date(2026, 10, 10)


def datos_validos(**cambios):
    datos = {
        "nombre": "Ana María", "apellido": "Pérez", "dni": "12345678",
        "cuil": "27123456784", "fecha_nacimiento": "15/03/1985",
        "domicilio": "San Martín 123", "email": "ana@correo.com",
        "caracter": "Titular",
    }
    datos.update(cambios)
    return datos


class TestValidarDocente(unittest.TestCase):

    def validar(self, **cambios):
        return validar_docente(**datos_validos(**cambios), hoy=HOY)

    def test_datos_validos_no_tienen_errores(self):
        errores, _ = self.validar()
        self.assertEqual(errores, {})

    def test_limpia_espacios_y_pasa_email_a_minusculas(self):
        errores, datos = self.validar(nombre="  Ana   María ", email=" ANA@Correo.com ")
        self.assertEqual(errores, {})
        self.assertEqual(datos["nombre"], "Ana María")
        self.assertEqual(datos["email"], "ana@correo.com")

    def test_campos_vacios(self):
        errores, _ = validar_docente("", "", "", "", "", "", "", "", hoy=HOY)
        self.assertEqual(set(errores), {
            "nombre", "apellido", "dni", "cuil", "fecha_nacimiento",
            "domicilio", "email", "caracter",
        })

    def test_nombre_con_numeros(self):
        errores, _ = self.validar(nombre="Ana2")
        self.assertIn("nombre", errores)

    def test_dni_con_letras_o_largo_incorrecto(self):
        self.assertIn("dni", self.validar(dni="12A45678")[0])
        self.assertIn("dni", self.validar(dni="123456")[0])

    def test_dni_de_7_numeros_con_cuil_correcto(self):
        errores, _ = self.validar(dni="1234567", cuil="20012345674")
        self.assertEqual(errores, {})

    def test_cuil_prefijo_invalido(self):
        errores, _ = self.validar(cuil="30123456784")
        self.assertIn("20, 23, 24 o 27", errores["cuil"])

    def test_cuil_no_coincide_con_dni(self):
        errores, _ = self.validar(cuil="27876543214")
        self.assertIn("no coincide", errores["cuil"])

    def test_menor_de_18_anios(self):
        errores, _ = self.validar(fecha_nacimiento="01/01/2015")
        self.assertIn("fecha_nacimiento", errores)

    def test_fecha_con_formato_incorrecto(self):
        errores, _ = self.validar(fecha_nacimiento="1985-03-15")
        self.assertIn("fecha_nacimiento", errores)

    def test_email_invalido(self):
        errores, _ = self.validar(email="ana@correo")
        self.assertIn("email", errores)

    def test_caracter_fuera_de_la_lista(self):
        errores, _ = validar_docente(**datos_validos(caracter="Otro"),
                                     caracteres_validos=["Titular", "Interino"], hoy=HOY)
        self.assertIn("caracter", errores)


class TestLimitesNacimiento(unittest.TestCase):

    def test_rango_de_18_a_100_anios(self):
        primera, ultima = limites_nacimiento(HOY)
        self.assertEqual(primera, date(1926, 1, 1))
        self.assertEqual(ultima, date(2008, 10, 10))


class TestCampoDuplicado(unittest.TestCase):

    def test_detecta_dni_duplicado(self):
        error = sqlite3.IntegrityError("UNIQUE constraint failed: docentes.dni")
        self.assertEqual(campo_duplicado(error)[0], "dni")

    def test_ignora_errores_que_no_son_unique(self):
        error = sqlite3.IntegrityError("FOREIGN KEY constraint failed")
        self.assertIsNone(campo_duplicado(error))


if __name__ == "__main__":
    unittest.main()
