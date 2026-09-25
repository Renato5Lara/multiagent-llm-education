def crear_saludo(nombre, saludo='Hola'):
    """Crea un saludo personalizado para una persona."""
    # Se devuelve el saludo seguido del nombre
    return f"{saludo}, {nombre}"

assert crear_saludo("Ana") == "Hola, Ana"
assert crear_saludo("Ana", saludo="Buenas") == "Buenas, Ana"
