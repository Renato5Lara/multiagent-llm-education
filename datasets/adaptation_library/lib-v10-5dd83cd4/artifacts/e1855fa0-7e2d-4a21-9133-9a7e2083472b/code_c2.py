def encontrar_mayor(numeros):
    """
    Encuentra el número mayor en una lista de números.

    Parámetros:
    numeros (list): Lista de números enteros.

    Retorna:
    int: El número mayor de la lista. Si la lista está vacía, retorna None.
    """
    # Manejo de caso límite: si la lista está vacía, retornar None
    if not numeros:
        return None
    
    # Tomar un candidato inicial, el primer elemento de la lista
    mayor = numeros[0]
    
    # Comparar cada número en la lista con el candidato actual
    for numero in numeros:
        # Si encontramos un número mayor, actualizar el candidato
        if numero > mayor:
            mayor = numero
    
    # Retornar el mayor encontrado
    return mayor

def ejemplo_uso():
    print(encontrar_mayor([3, 7, 2]))  # Debería imprimir 7
    print(encontrar_mayor([-1, -5, -2]))  # Debería imprimir -1
    print(encontrar_mayor([]))  # Debería imprimir None
    print(encontrar_mayor([0, 0, 0]))  # Debería imprimir 0
    print(encontrar_mayor([100, 200, 300]))  # Debería imprimir 300
