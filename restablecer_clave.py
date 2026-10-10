"""Quita la contraseña de acceso si se olvidó.

Cerrá el sistema y ejecutá:  python restablecer_clave.py
La próxima vez que abras el sistema te va a pedir crear una contraseña nueva.
(Quien pueda ejecutar este archivo ya tiene acceso al archivo Gestion.db.)
"""
from database.ajustes import borrar_clave_acceso  # noqa: E402

if __name__ == "__main__":
    respuesta = input("Esto elimina la contraseña actual. Escribí SI para continuar: ")
    if respuesta.strip().upper() == "SI":
        borrar_clave_acceso()
        print("Listo. Al abrir el sistema podrás crear una contraseña nueva.")
    else:
        print("No se hizo ningún cambio.")
