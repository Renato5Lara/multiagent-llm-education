def contar_hasta(n):
    """Devuelve una lista de números del 1 hasta n."""
    resultado = []  # Inicializa una lista vacía para almacenar los números
    contador = 1  # Comienza el contador en 1
    while contador <= n:  # Mientras el contador sea menor o igual a n
        resultado.append(contador)  # Agrega el contador a la lista
        contador += 1  # Incrementa el contador en 1
    return resultado  # Devuelve la lista con los números

assert contar_hasta(3) == [1, 2, 3]
