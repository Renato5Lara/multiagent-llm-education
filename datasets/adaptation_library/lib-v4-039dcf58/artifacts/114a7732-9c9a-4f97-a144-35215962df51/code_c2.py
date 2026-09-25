def aprobo(nota):
    """
    Determina si un estudiante aprueba o no basado en su nota.
    
    Parámetros:
    nota (int): La nota del estudiante.
    
    Retorna:
    bool: True si la nota es mayor o igual a 11, False en caso contrario.
    """
    # Verificamos si la nota es un número válido
    if nota is None:  # Caso límite: entrada vacía
        return False
    if nota < 0:  # Caso límite: nota negativa
        return False
    if nota > 20:  # Caso límite: nota excesiva
        return False
    
    # Comparamos la nota con el umbral de aprobación
    return nota >= 11  # Retorna True si aprueba, False si no

def ejemplo_uso():
    """
    Función que ilustra el uso de la función aprobo.
    """
    print(aprobo(11))  # Debería imprimir True
    print(aprobo(10))  # Debería imprimir False
    print(aprobo(15))  # Debería imprimir True
    print(aprobo(0))   # Debería imprimir False
    print(aprobo(-5))  # Debería imprimir False
    print(aprobo(25))  # Debería imprimir False
    print(aprobo(None))  # Debería imprimir False
