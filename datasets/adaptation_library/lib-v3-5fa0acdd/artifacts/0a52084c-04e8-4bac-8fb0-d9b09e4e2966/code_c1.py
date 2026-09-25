def saludar(nombre):
    """Devuelve un saludo personalizado para el nombre dado."""
    # Se crea el mensaje de saludo concatenando "Hola, " con el nombre
    mensaje = "Hola, " + nombre
    # Se retorna el mensaje de saludo
    return mensaje

assert saludar("Ana") == "Hola, Ana"
assert saludar("Luis") == "Hola, Luis"
