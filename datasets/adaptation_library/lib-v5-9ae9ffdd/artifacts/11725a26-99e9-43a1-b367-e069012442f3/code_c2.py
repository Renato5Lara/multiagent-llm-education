def clasificar_nota(nota):
    """
    Clasifica la nota en categorías.
    
    Parámetros:
    nota (int): La nota a clasificar.
    
    Retorna:
    str: La clasificación de la nota.
    """
    # Verificamos si la nota es un número válido
    if nota is None:
        return "entrada vacía"
    if nota < 0:
        return "nota negativa"
    if nota > 20:
        return "nota excesiva"
    
    # Clasificación de la nota
    if nota >= 17:
        return "excelente"  # Nota alta
    elif nota >= 10:
        return "regular"    # Nota media
    else:
        return "deficiente"  # Nota baja

def ejemplo_uso():
    # Ejemplos de uso de la función clasificar_nota
    print(clasificar_nota(18))  # Debe imprimir "excelente"
    print(clasificar_nota(12))  # Debe imprimir "regular"
    print(clasificar_nota(5))   # Debe imprimir "deficiente"
    print(clasificar_nota(-1))  # Debe imprimir "nota negativa"
    print(clasificar_nota(25))  # Debe imprimir "nota excesiva"
    print(clasificar_nota(None)) # Debe imprimir "entrada vacía"

assert clasificar_nota(18) == "excelente"
assert clasificar_nota(12) == "regular"
