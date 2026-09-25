def saludar(nombre):
    """
    Función que genera un saludo personalizado.
    
    Parámetros:
    nombre (str): El nombre de la persona a saludar.
    
    Retorna:
    str: Un saludo en forma de cadena.
    """
    # Verificamos si el nombre está vacío
    if not nombre:
        return "Hola, invitado"  # Saludo por defecto si no se proporciona un nombre
    
    # Generamos el saludo utilizando el nombre proporcionado
    return f"Hola, {nombre}"

def ejemplo_uso():
    # Ejemplo de uso de la función saludar
    print(saludar("Ana"))  # Debería imprimir: Hola, Ana
    print(saludar("Luis"))  # Debería imprimir: Hola, Luis
    print(saludar(""))      # Debería imprimir: Hola, invitado
    print(saludar("Carlos"))  # Debería imprimir: Hola, Carlos

assert saludar("Ana") == "Hola, Ana"
assert saludar("Luis") == "Hola, Luis"
