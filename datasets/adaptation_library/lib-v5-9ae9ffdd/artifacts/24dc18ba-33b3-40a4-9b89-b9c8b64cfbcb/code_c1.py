def calcular_promedio_ponderado(n1, n2, n3):
    """Calcula el promedio ponderado de tres notas."""
    # Definimos los pesos para cada nota
    peso1 = 0.3
    peso2 = 0.3
    peso3 = 0.4
    
    # Calculamos el promedio ponderado
    promedio = (n1 * peso1 + n2 * peso2 + n3 * peso3) / (peso1 + peso2 + peso3)
    
    return promedio

assert calcular_promedio_ponderado(10, 10, 10) == 10
