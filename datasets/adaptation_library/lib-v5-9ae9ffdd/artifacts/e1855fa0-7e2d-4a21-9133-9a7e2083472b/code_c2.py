def encontrar_mayor(numeros):
    """
    Encuentra el número mayor en una lista de números.

    Parámetros:
    numeros (list): Una lista de números enteros.

    Retorna:
    int: El número mayor de la lista. Si la lista está vacía, retorna None.
    """
    # Verificamos si la lista está vacía
    if not numeros:
        return None  # Retornamos None si no hay elementos

    # Inicializamos la variable mayor con el primer elemento de la lista
    mayor = numeros[0]

    # Iteramos sobre cada número en la lista
    for numero in numeros:
        # Comparamos el número actual con el mayor encontrado hasta ahora
        if numero > mayor:
            mayor = numero  # Actualizamos el mayor si encontramos un número mayor

    return mayor  # Retornamos el número mayor encontrado

def ejemplo_uso():
    # Ejemplo de uso de la función encontrar_mayor
    print(encontrar_mayor([3, 7, 2]))  # Debería imprimir 7
    print(encontrar_mayor([-1, -5, -2]))  # Debería imprimir -1
    print(encontrar_mayor([]))  # Debería imprimir None
    print(encontrar_mayor([0, 0, 0]))  # Debería imprimir 0
    print(encontrar_mayor([100, 200, 300, 400]))  # Debería imprimir 400

assert encontrar_mayor([3, 7, 2]) == 7
assert encontrar_mayor([-1, -5, -2]) == -1
