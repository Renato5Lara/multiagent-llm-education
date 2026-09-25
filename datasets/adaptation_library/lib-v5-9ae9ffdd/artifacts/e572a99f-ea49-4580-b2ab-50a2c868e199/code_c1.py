def tabla_multiplicar(n):
    """Genera una tabla de multiplicar de tamaño n x n."""
    tabla = []  # Inicializa una lista vacía para almacenar las filas de la tabla
    for i in range(1, n + 1):  # Itera desde 1 hasta n
        fila = []  # Inicializa una lista vacía para la fila actual
        for j in range(1, n + 1):  # Itera desde 1 hasta n para las columnas
            fila.append(i * j)  # Calcula el producto y lo añade a la fila
        tabla.append(fila)  # Añade la fila completa a la tabla
    return tabla  # Devuelve la tabla completa

assert tabla_multiplicar(2) == [[1, 2], [2, 4]]
