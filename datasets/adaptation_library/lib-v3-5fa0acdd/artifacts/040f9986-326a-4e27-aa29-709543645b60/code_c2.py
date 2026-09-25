def sumar_lista(numeros):
    """
    Suma todos los elementos de una lista de números.

    Parámetros:
    numeros (list): Lista de números a sumar.

    Retorna:
    int: La suma de los números en la lista. Si la lista está vacía, retorna 0.
    """
    # Inicializamos la suma en 0
    suma = 0
    
    # Verificamos si la lista está vacía
    if not numeros:
        return suma  # Retornamos 0 si la lista está vacía
    
    # Iteramos sobre cada número en la lista
    for numero in numeros:
        suma += numero  # Sumamos el número actual a la suma total
    
    return suma  # Retornamos la suma total

def ejemplo_uso():
    # Ejemplo de uso de la función sumar_lista
    print(sumar_lista([1, 2, 3]))  # Debería imprimir 6
    print(sumar_lista([]))          # Debería imprimir 0
    print(sumar_lista([0, 0, 0]))   # Debería imprimir 0
    print(sumar_lista([100, 200]))  # Debería imprimir 300
    print(sumar_lista([-1, 1]))     # Debería imprimir 0

assert sumar_lista([1, 2, 3]) == 6
