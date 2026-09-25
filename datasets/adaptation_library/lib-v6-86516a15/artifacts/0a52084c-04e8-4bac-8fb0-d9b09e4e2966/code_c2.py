def saludar(nombre):
    """Función que devuelve un saludo personalizado."""
    # Verificamos si el nombre está vacío
    if not nombre:
        return "Hola, invitado"  # Saludo por defecto si no se proporciona un nombre
    # Retornamos el saludo personalizado
    return f"Hola, {nombre}"

def ejemplo_uso():
    """Función que ilustra el uso de la función saludar."""
    print(saludar("Ana"))  # Debería imprimir: Hola, Ana
    print(saludar("Luis"))  # Debería imprimir: Hola, Luis
    print(saludar(""))      # Debería imprimir: Hola, invitado

resultado = saludar('Ana')
