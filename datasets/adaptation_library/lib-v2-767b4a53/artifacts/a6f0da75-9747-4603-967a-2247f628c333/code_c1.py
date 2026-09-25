def suma_hasta(n):
    """Calcula la suma de todos los números enteros desde 1 hasta n."""
    total = 0  # Inicializa la variable total en 0
    for i in range(1, n + 1):  # Itera desde 1 hasta n, inclusive
        total += i  # Suma el valor de i al total
    return total  # Devuelve el total acumulado

assert suma_hasta(5) == 15
assert suma_hasta(1) == 1
