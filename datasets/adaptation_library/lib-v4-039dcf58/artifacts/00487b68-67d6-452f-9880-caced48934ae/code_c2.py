def es_par(numero):
    """
    Determina si un número es par.

    Args:
        numero (int): El número a evaluar.

    Returns:
        bool: True si el número es par, False si es impar.
    """
    # Verificamos si el número es un entero
    if not isinstance(numero, int):
        raise ValueError("El argumento debe ser un número entero.")
    
    # Un número es par si el residuo de dividirlo entre 2 es 0
    return numero % 2 == 0

def repartir_exacto(total, personas):
    """
    Calcula cuántas unidades le corresponden a cada persona al repartir un total.

    Args:
        total (int): La cantidad total a repartir.
        personas (int): El número de personas entre las que se reparte.

    Returns:
        int: La cantidad que le corresponde a cada persona.
    """
    # Verificamos que el total y las personas sean enteros
    if not isinstance(total, int) or not isinstance(personas, int):
        raise ValueError("Ambos argumentos deben ser números enteros.")
    
    # Manejo de casos límite
    if personas <= 0:
        raise ValueError("El número de personas debe ser mayor que cero.")
    
    # Calculamos la cantidad que le corresponde a cada persona
    return total // personas  # División entera

def ejemplo_uso():
    """
    Función que ilustra el uso de las funciones es_par y repartir_exacto.
    """
    print("Ejemplo de uso de es_par:")
    print("4 es par:", es_par(4))  # Debe ser True
    print("7 es par:", es_par(7))  # Debe ser False

    print("\nEjemplo de uso de repartir_exacto:")
    print("Repartir 10 entre 3 personas:", repartir_exacto(10, 3))  # Debe ser 3

assert es_par(4) is True
assert es_par(7) is False
assert repartir_exacto(10, 3) == 3
