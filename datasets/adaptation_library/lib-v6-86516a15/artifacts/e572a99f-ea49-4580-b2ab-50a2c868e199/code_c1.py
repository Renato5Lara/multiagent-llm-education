def tabla_multiplicar(n):
    """Genera una tabla de multiplicar de tamaño n."""
    tabla = []  # Inicializa la lista que contendrá las filas de la tabla
    for i in range(1, n + 1):  # Itera desde 1 hasta n
        fila = []  # Inicializa la fila actual
        for j in range(1, n + 1):  # Itera desde 1 hasta n para crear la fila
            fila.append(i * j)  # Agrega el producto a la fila
        tabla.append(fila)  # Agrega la fila completa a la tabla
    return tabla  # Devuelve la tabla completa
