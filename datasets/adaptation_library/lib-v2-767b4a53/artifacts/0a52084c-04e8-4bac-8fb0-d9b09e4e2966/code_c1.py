def saludar(nombre):
    """Devuelve un saludo personalizado para el nombre dado."""
    # Se crea el saludo concatenando "Hola, " con el nombre
    saludo = "Hola, " + nombre
    # Se retorna el saludo generado
    return saludo

assert saludar("Ana") == "Hola, Ana"
assert saludar("Luis") == "Hola, Luis"
