def crear_saludo(nombre, saludo='Hola'):
    """
    Crea un saludo personalizado.

    Parámetros:
    nombre (str): El nombre de la persona a saludar.
    saludo (str): La frase de saludo. Por defecto es 'Hola'.

    Retorna:
    str: Un saludo en formato 'saludo, nombre'.
    """
    # Verificamos si el nombre está vacío
    if not nombre:
        return "Nombre no puede estar vacío"
    
    # Retornamos el saludo formateado
    return f"{saludo}, {nombre}"

def ejemplo_uso():
    # Ejemplo de uso de la función crear_saludo
    print(crear_saludo("Ana"))  # Debería imprimir: Hola, Ana
    print(crear_saludo("Ana", saludo="Buenas"))  # Debería imprimir: Buenas, Ana
    print(crear_saludo(""))  # Debería imprimir: Nombre no puede estar vacío

assert crear_saludo("Ana") == "Hola, Ana"
assert crear_saludo("Ana", saludo="Buenas") == "Buenas, Ana"
