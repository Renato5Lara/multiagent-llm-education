def sumar_lista(numeros):
    """Suma todos los elementos de una lista de números."""
    suma = 0  # Inicializamos la variable suma en 0
    for numero in numeros:  # Iteramos sobre cada número en la lista
        suma += numero  # Sumamos el número actual a la suma total
    return suma  # Devolvemos la suma total

assert sumar_lista([1, 2, 3]) == 6
