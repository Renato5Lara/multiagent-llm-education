def calcular_area_rectangulo(base, altura):
    """
    Calcula el área de un rectángulo dado su base y altura.

    Parámetros:
    base (float): La longitud de la base del rectángulo.
    altura (float): La longitud de la altura del rectángulo.

    Retorna:
    float: El área del rectángulo. Si la base o la altura son menores o iguales a cero, retorna 0.
    """
    # Verificamos si la base o la altura son menores o iguales a cero
    if base <= 0 or altura <= 0:
        return 0  # Retornamos 0 en caso de valores no válidos

    # Calculamos el área multiplicando la base por la altura
    area = base * altura
    return area  # Retornamos el área calculada

def ejemplo_uso():
    # Ejemplo de uso de la función calcular_area_rectangulo
    print("Área del rectángulo con base 4 y altura 5:", calcular_area_rectangulo(4, 5))
    print("Área del rectángulo con base 0 y altura 5:", calcular_area_rectangulo(0, 5))
    print("Área del rectángulo con base 4 y altura -3:", calcular_area_rectangulo(4, -3))
    print("Área del rectángulo con base 10 y altura 10:", calcular_area_rectangulo(10, 10))

assert calcular_area_rectangulo(4, 5) == 20
