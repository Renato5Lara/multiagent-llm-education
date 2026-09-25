def suma_hasta(n):
    """Suma los números del 1 al n."""
    total = 0  # Inicializa el total en 0
    for i in range(1, n + 1):  # Itera desde 1 hasta n
        total += i  # Suma el valor actual de i al total
    return total  # Devuelve el total acumulado
