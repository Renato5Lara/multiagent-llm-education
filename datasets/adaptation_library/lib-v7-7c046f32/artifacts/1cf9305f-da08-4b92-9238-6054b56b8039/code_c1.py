def procesar_promedio(notas):
    """Calcula el promedio de una lista de notas."""
    suma = sum(notas)  # Sumar todas las notas
    cantidad = len(notas)  # Contar la cantidad de notas
    promedio = suma / cantidad  # Calcular el promedio
    return promedio  # Retornar el promedio calculado
