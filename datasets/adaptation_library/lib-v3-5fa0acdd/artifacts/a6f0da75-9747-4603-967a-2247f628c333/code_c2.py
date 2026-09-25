def suma_hasta(n):
    """
    Calcula la suma de todos los números enteros desde 1 hasta n.
    
    Parámetros:
    n (int): El número hasta el cual se sumarán los enteros.
    
    Retorna:
    int: La suma de los enteros desde 1 hasta n.
    """
    # Manejo de caso límite: si n es menor que 1, retornamos 0
    if n < 1:
        return 0
    
    suma = 0  # Inicializamos la variable suma en 0
    
    # Iteramos desde 1 hasta n (inclusive)
    for i in range(1, n + 1):
        suma += i  # Sumamos el valor actual a la suma
    
    return suma  # Retornamos el resultado final

def ejemplo_uso():
    """
    Función que ilustra el uso de la función suma_hasta.
    """
    print("La suma de los números hasta 5 es:", suma_hasta(5))  # Debe imprimir 15
    print("La suma de los números hasta 1 es:", suma_hasta(1))  # Debe imprimir 1
    print("La suma de los números hasta 0 es:", suma_hasta(0))  # Debe imprimir 0
    print("La suma de los números hasta -3 es:", suma_hasta(-3))  # Debe imprimir 0

assert suma_hasta(5) == 15
assert suma_hasta(1) == 1
