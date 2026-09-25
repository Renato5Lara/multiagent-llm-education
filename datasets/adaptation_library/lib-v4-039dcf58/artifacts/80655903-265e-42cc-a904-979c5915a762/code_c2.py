def contar_hasta(n):
    """
    Función que cuenta desde 1 hasta n y devuelve una lista con los números contados.
    
    Parámetros:
    n (int): El número hasta el cual contar. Debe ser un entero positivo.
    
    Retorna:
    list: Una lista de enteros desde 1 hasta n.
    """
    # Verificamos si n es menor o igual a 0
    if n <= 0:
        return []  # Retornamos una lista vacía para casos no válidos
    
    # Inicializamos una lista vacía para almacenar los números
    numeros = []
    
    # Usamos un contador para contar desde 1 hasta n
    contador = 1
    while contador <= n:  # Mientras el contador sea menor o igual a n
        numeros.append(contador)  # Agregamos el contador a la lista
        contador += 1  # Incrementamos el contador
    
    return numeros  # Retornamos la lista con los números contados

def ejemplo_uso():
    """
    Función que ilustra el uso de la función contar_hasta.
    """
    print(contar_hasta(3))  # Debería imprimir [1, 2, 3]
    print(contar_hasta(0))  # Debería imprimir []
    print(contar_hasta(-5))  # Debería imprimir []
    print(contar_hasta(5))  # Debería imprimir [1, 2, 3, 4, 5]
