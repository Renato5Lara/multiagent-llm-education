def leer_edad(texto_ingresado):
    """
    Convierte una cadena de texto que representa una edad en un número entero.
    
    Parámetros:
    texto_ingresado (str): La cadena que contiene la edad a convertir.
    
    Retorna:
    int: La edad como un número entero.
    
    Si la entrada es vacía o no es un número válido, se retorna 0.
    """
    # Verificamos si la entrada está vacía
    if texto_ingresado.strip() == "":
        return 0  # Retornamos 0 si la entrada está vacía
    
    try:
        # Intentamos convertir la cadena a un entero
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
    print(leer_edad(""))    # Debería imprimir 0
    print(leer_edad("-5"))  # Debería imprimir 0
    print(leer_edad("abc")) # Debería imprimir 0
