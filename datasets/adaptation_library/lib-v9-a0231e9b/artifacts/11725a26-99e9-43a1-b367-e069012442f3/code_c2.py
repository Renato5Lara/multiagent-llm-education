def clasificar_nota(nota):
    """
    Clasifica la nota en 'excelente' o 'regular'.
    
    Parámetros:
    nota (float): La nota a clasificar.
    
    Retorna:
    str: 'excelente' si la nota es mayor o igual a 17, 'regular' en caso contrario.
    """
    # Verificamos si la nota es un número válido
    if nota is None:
        return "Entrada no válida"
    
    # Clasificamos la nota
    if nota >= 17:  # Si la nota es mayor o igual a 17
        return "excelente"  # Retornamos 'excelente'
    else:  # En caso contrario
        return "regular"  # Retornamos 'regular'

def ejemplo_uso():
    # Ejemplo de uso de la función clasificar_nota
    print(clasificar_nota(18))  # Debería imprimir 'excelente'
    print(clasificar_nota(12))  # Debería imprimir 'regular'
