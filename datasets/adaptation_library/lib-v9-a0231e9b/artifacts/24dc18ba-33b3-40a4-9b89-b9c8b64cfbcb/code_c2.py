def calcular_promedio_ponderado(n1, n2, n3):
    """
    Calcula el promedio ponderado de tres notas.
    
    Parámetros:
    n1 (float): Primera nota.
    n2 (float): Segunda nota.
    n3 (float): Tercera nota.
    
    Retorna:
    float: El promedio ponderado de las tres notas.
    
    Nota: Los paréntesis alrededor de (n1 + n2 + n3) son necesarios para asegurar que la suma se realice antes de la división.
    Sin los paréntesis, la división podría ocurrir antes de la suma, alterando el resultado final.
    """
    # Verificar si las notas son válidas (no vacías y no negativas)
    if n1 is None or n2 is None or n3 is None:
        return None  # Retorna None si alguna nota es None
    if n1 < 0 or n2 < 0 or n3 < 0:
        return None  # Retorna None si alguna nota es negativa
    
    # Calcular el promedio ponderado
    total_notas = n1 + n2 + n3  # Sumar las notas
    promedio = total_notas / 3  # Dividir la suma entre 3 para obtener el promedio
    return promedio  # Retornar el promedio calculado

def ejemplo_uso():
    print(calcular_promedio_ponderado(10, 10, 10))  # Debería imprimir 10.0
    print(calcular_promedio_ponderado(0, 0, 0))      # Debería imprimir 0.0
    print(calcular_promedio_ponderado(5, 10, 15))    # Debería imprimir 10.0
    print(calcular_promedio_ponderado(None, 10, 10)) # Debería imprimir None
    print(calcular_promedio_ponderado(-1, 10, 10))   # Debería imprimir None
