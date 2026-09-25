def convertir_a_numero(texto):
    """
    Convierte una cadena de texto a un número entero o flotante.
    
    Parámetros:
    texto (str): La cadena que se desea convertir a número.
    
    Retorna:
    int o float: El número convertido, o None si la conversión falla.
    """
    # Verificamos si el texto está vacío
    if texto == "":
        return None  # Retornamos None si la entrada está vacía
    
    # Intentamos convertir el texto a un número
    try:
        # Primero intentamos convertir a float
        numero = float(texto)
        # Si el número es entero, lo convertimos a int
        if numero.is_integer():
            return int(numero)
        return numero  # Retornamos el número como float
    except ValueError:
        return None  # Retornamos None si la conversión falla

def ejemplo_uso():
    """
    Función que ilustra el uso de la función convertir_a_numero.
    """
    print(convertir_a_numero("10"))    # Debería imprimir 10
    print(convertir_a_numero("3.5"))   # Debería imprimir 3.5
    print(convertir_a_numero(""))       # Debería imprimir None
    print(convertir_a_numero("abc"))    # Debería imprimir None
    print(convertir_a_numero("0"))      # Debería imprimir 0
    print(convertir_a_numero("1000000"))  # Debería imprimir 1000000
    print(convertir_a_numero("1e3"))    # Debería imprimir 1000.0

assert convertir_a_numero("10") == 10
assert convertir_a_numero("3.5") == 3.5
