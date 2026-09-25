def contar_hasta(n):
    """Cuenta desde 1 hasta n y devuelve una lista con los números."""
    contador = 1  # Inicializa el contador en 1
    numeros = []  # Lista para almacenar los números contados
    while contador <= n:  # Mientras el contador sea menor o igual a n
        numeros.append(contador)  # Agrega el contador a la lista
        contador += 1  # Incrementa el contador en 1
    return numeros  # Devuelve la lista de números contados
