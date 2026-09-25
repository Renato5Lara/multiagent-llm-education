def calcular_promedio_ponderado(n1, n2, n3):
    """Calcula el promedio ponderado de tres notas."""
    suma = n1 + n2 + n3  # Suma de las notas
    promedio = suma / 3  # División de la suma entre 3 para obtener el promedio
    return promedio  # Retorna el promedio calculado

# Los paréntesis alrededor de (2 + 3 + 5) son necesarios para asegurar que la suma se realice antes de la división.
# Sin paréntesis, la división ocurriría antes que la última suma, cambiando el resultado.
