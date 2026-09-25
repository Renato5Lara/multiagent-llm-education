def calcular_area_rectangulo(base, altura):
    """
    Calcula el área de un rectángulo dado su base y altura.

    Parámetros:
    base (float): La base del rectángulo.
    altura (float): La altura del rectángulo.

    Retorna:
    float: El área del rectángulo calculada como base * altura.
    """
    # Verificar si la base o la altura son cero o negativos
    if base <= 0 or altura <= 0:
        return 0  # El área no puede ser negativa o cero

    # Calcular el área multiplicando base por altura
    area = base * altura
    return area

def ejemplo_uso():
    # Ejemplo de uso de la función calcular_area_rectangulo
    print(calcular_area_rectangulo(6, 3))  # Debería imprimir 18
    print(calcular_area_rectangulo(4, 5))  # Debería imprimir 20
    print(calcular_area_rectangulo(0, 5))  # Debería imprimir 0
    print(calcular_area_rectangulo(4, -2))  # Debería imprimir 0
    print(calcular_area_rectangulo(10, 10))  # Debería imprimir 100
