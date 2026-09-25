def sumar_lista(numeros):
    """Suma los elementos de una lista."""
    total = 0  # Inicializa el total en 0
    for numero in numeros:  # Itera sobre cada número en la lista
        total += numero  # Suma el número actual al total
        # Traza el valor de total en cada vuelta
    return total  # Devuelve el total final

# Estado inicial a nivel de módulo
resultado = sumar_lista([1, 2, 3])  # Esto se puede usar para verificar el resultado en un entorno de prueba.
