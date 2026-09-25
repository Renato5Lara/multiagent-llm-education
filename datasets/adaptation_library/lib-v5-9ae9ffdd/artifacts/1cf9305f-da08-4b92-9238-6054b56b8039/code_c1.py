def procesar_promedio(notas):
    """Calcula el promedio de una lista de notas."""
    suma = sum(notas)  # Sumar todas las notas
    cantidad = len(notas)  # Contar cuántas notas hay
    promedio = suma / cantidad  # Calcular el promedio
    return promedio  # Devolver el promedio calculado

assert procesar_promedio([10, 20, 30]) == 20
