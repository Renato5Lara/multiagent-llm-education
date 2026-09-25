def suma_hasta(n):
    """
    Suma todos los números enteros desde 1 hasta n.

    Parámetros:
    n (int): El número hasta el cual se sumarán los enteros.

    Retorna:
    int: La suma de los números desde 1 hasta n. Si n es menor que 1, retorna 0.
    """
    # Verificamos si n es menor que 1
    if n < 1:
        return 0  # Retornamos 0 si n es menor que 1

    total = 0  # Inicializamos la variable total en 0
    # Iteramos desde 1 hasta n (inclusive)
    for i in range(1, n + 1):
        total += i  # Sumamos el valor actual de i al total

    return total  # Retornamos el total acumulado

def ejemplo_uso():
    print(suma_hasta(5))  # Debería imprimir 15
    print(suma_hasta(1))  # Debería imprimir 1
    print(suma_hasta(0))  # Debería imprimir 0
    print(suma_hasta(-3))  # Debería imprimir 0
