def leer_edad(texto_ingresado):
    """Convierte un texto ingresado a un número entero que representa la edad."""
    # Convierte el texto ingresado a un número entero
    edad = int(texto_ingresado)
    # Devuelve la edad como un número entero
    return edad

assert leer_edad("18") == 18
assert leer_edad("25") == 25
