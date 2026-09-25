def leer_edad(texto_ingresado):
    """Convierte un texto ingresado a un número entero que representa la edad."""
    # Convierte el texto ingresado a un entero
    edad = int(texto_ingresado)
    return edad  # Devuelve la edad como un número entero

# Estado inicial a nivel de módulo
edad1 = leer_edad("18")
edad2 = leer_edad("25")
