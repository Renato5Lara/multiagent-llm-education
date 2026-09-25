def leer_edad(texto_ingresado):
    """
    Convierte un texto ingresado a un entero que representa la edad.
    
    Parámetros:
    texto_ingresado (str): El texto que se desea convertir a un entero.
    
    Retorna:
    int: La edad como un número entero.
    
    Si el texto ingresado está vacío o no es un número válido, se retorna 0.
    """
    # Verificamos si el texto ingresado está vacío
    if texto_ingresado.strip() == "":
        return 0  # Retornamos 0 si la entrada está vacía
    
    try:
        # Intentamos convertir el texto a un entero
        edad = int(texto_ingresado)
        
        # Verificamos si la edad es negativa
        if edad < 0:
            return 0  # Retornamos 0 si la edad es negativa
        
        return edad  # Retornamos la edad válida
    except ValueError:
        # Si ocurre un error en la conversión, retornamos 0
        return 0

def ejemplo_uso():
    # Ejemplo de uso de la función leer_edad
    print(leer_edad("18"))  # Debería imprimir 18
    print(leer_edad("25"))  # Debería imprimir 25
    print(leer_edad(""))     # Debería imprimir 0
    print(leer_edad("-5"))   # Debería imprimir 0
    print(leer_edad("abc"))  # Debería imprimir 0
