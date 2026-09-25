def encontrar_mayor(numeros):
    """Devuelve el número mayor de una lista de números."""
    mayor = numeros[0]  # Inicializa la variable mayor con el primer elemento de la lista
    for numero in numeros:  # Recorre cada número en la lista
        if numero > mayor:  # Compara el número actual con el mayor encontrado
            mayor = numero  # Actualiza mayor si se encuentra un número más grande
    return mayor  # Devuelve el número mayor encontrado

assert encontrar_mayor([3, 7, 2]) == 7
assert encontrar_mayor([-1, -5, -2]) == -1
