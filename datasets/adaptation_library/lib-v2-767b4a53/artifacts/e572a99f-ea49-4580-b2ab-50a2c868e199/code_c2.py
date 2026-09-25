def tabla_multiplicar(n):
    """
    Genera una tabla de multiplicar de tamaño n x n.
    
    Parámetros:
    n (int): El tamaño de la tabla de multiplicar.
    
    Retorna:
    list: Una lista de listas que representa la tabla de multiplicar.
    """
    # Manejo de casos límite
    if n <= 0:  # Si n es cero o negativo, retornamos una lista vacía
        return []
    
    # Inicializamos la tabla vacía
    tabla = []
    
    # Creamos la tabla de multiplicar
    for i in range(1, n + 1):  # Iteramos desde 1 hasta n
        fila = []  # Inicializamos una nueva fila
        for j in range(1, n + 1):  # Iteramos desde 1 hasta n para las columnas
            fila.append(i * j)  # Agregamos el producto a la fila
        tabla.append(fila)  # Agregamos la fila a la tabla
    
    return tabla  # Retornamos la tabla completa

def ejemplo_uso():
    # Ejemplo de uso de la función tabla_multiplicar
    print(tabla_multiplicar(2))  # Debería imprimir [[1, 2], [2, 4]]
    print(tabla_multiplicar(3))  # Debería imprimir [[1, 2, 3], [2, 4, 6], [3, 6, 9]]
    print(tabla_multiplicar(0))  # Debería imprimir []
    print(tabla_multiplicar(-1))  # Debería imprimir []
