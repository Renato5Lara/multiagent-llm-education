def suma_hasta(n):
    """Calcula la suma de todos los números enteros desde 1 hasta n."""
    suma = 0  # Inicializamos la variable suma en 0
    for i in range(1, n + 1):  # Iteramos desde 1 hasta n, inclusive
        suma += i  # Sumamos el valor de i a la suma
    return suma  # Devolvemos el resultado final de la suma

assert suma_hasta(5) == 15
assert suma_hasta(1) == 1
