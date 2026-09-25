def convertir_a_numero(texto):
    """
    Convierte una cadena de texto a un número entero o flotante.
    
    Si el texto representa un número entero (sin punto decimal), se convierte a int.
    Si el texto representa un número decimal (con punto decimal), se convierte a float.
    
    Parámetros:
    texto (str): La cadena de texto que se desea convertir a número.
    
    Retorna:
    int o float: El número convertido.
    """
    # Verificamos si el texto está vacío
    if texto == "":
        return None  # Retornamos None si la entrada está vacía
    
    # Intentamos convertir el texto a un número entero
    try:
        numero_entero = int(texto)  # Intentamos convertir a int
        return numero_entero  # Retornamos el número entero si la conversión fue exitosa
    except ValueError:
        # Si falla la conversión a int, intentamos convertir a float
        try:
            numero_flotante = float(texto)  # Intentamos convertir a float
            return numero_flotante  # Retornamos el número flotante si la conversión fue exitosa
        except ValueError:
            return None  # Retornamos None si la conversión falla

def ejemplo_uso():
    # Ejemplo de uso de la función convertir_a_numero
    print(convertir_a_numero("10"))  # Debería imprimir 10
    print(convertir_a_numero("3.5"))  # Debería imprimir 3.5
    print(convertir_a_numero(""))  # Debería imprimir None
    print(convertir_a_numero("abc"))  # Debería imprimir None
    print(convertir_a_numero("0"))  # Debería imprimir 0
    print(convertir_a_numero("1000000000"))  # Debería imprimir 1000000000
    print(convertir_a_numero("1.5e10"))  # Debería imprimir 15000000000.0
