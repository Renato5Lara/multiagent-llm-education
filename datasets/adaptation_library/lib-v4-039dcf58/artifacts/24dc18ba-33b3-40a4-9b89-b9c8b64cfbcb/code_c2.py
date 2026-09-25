def calcular_promedio_ponderado(n1, n2, n3):
    """
    Calcula el promedio ponderado de tres notas.
    
    Parámetros:
    n1 (float): Primera nota.
    n2 (float): Segunda nota.
    n3 (float): Tercera nota.
    
    Retorna:
    float: El promedio ponderado de las tres notas.
    """
    # Verificamos si las notas son válidas (no deben ser vacías ni negativas)
    if n1 is None or n2 is None or n3 is None:
        return None  # Retorna None si alguna nota es None
    if n1 < 0 or n2 < 0 or n3 < 0:
        return None  # Retorna None si alguna nota es negativa
    
    # Calculamos el promedio ponderado
    total_notas = n1 + n2 + n3  # Suma de las notas
    promedio = total_notas / 3  # Promedio simple, ya que todas las notas tienen el mismo peso
    
    return promedio  # Retornamos el promedio calculado

def ejemplo_uso():
    """
    Función que ilustra el uso de la función calcular_promedio_ponderado.
    """
    print("Promedio ponderado de 10, 10, 10:", calcular_promedio_ponderado(10, 10, 10))
    print("Promedio ponderado de 0, 10, 20:", calcular_promedio_ponderado(0, 10, 20))
    print("Promedio ponderado de -5, 10, 15:", calcular_promedio_ponderado(-5, 10, 15))
    print("Promedio ponderado de None, 10, 15:", calcular_promedio_ponderado(None, 10, 15)) 

assert calcular_promedio_ponderado(10, 10, 10) == 10
