def suma_hasta(n):
    """
    Calcula la suma de todos los números enteros desde 1 hasta n.
    
    Parámetros:
    n (int): El número hasta el cual se sumarán los enteros.
    
    Retorna:
    int: La suma de los enteros desde 1 hasta n.
    """
    # Verificamos si n es menor que 0, en cuyo caso la suma es 0
    if n < 0:
        return 0
    
    # Inicializamos la variable suma en 0
    suma = 0
    
    # Iteramos desde 1 hasta n (inclusive)
    for i in range(1, n + 1):
        suma += i  # Sumamos el valor actual a la suma total
    
    return suma  # Retornamos la suma total

def ejemplo_uso():
    """
    Función que ilustra el uso de la función suma_hasta.
    """
    print("Suma hasta 5:", suma_hasta(5))  # Debería imprimir 15
    print("Suma hasta 1:", suma_hasta(1))  # Debería imprimir 1
    print("Suma hasta 0:", suma_hasta(0))  # Debería imprimir 0
    print("Suma hasta -3:", suma_hasta(-3))  # Debería imprimir 0
    print("Suma hasta 10:", suma_hasta(10))  # Debería imprimir 55

assert suma_hasta(5) == 15
assert suma_hasta(1) == 1
