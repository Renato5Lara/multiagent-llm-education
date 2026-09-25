def es_par(numero):
    """Determina si un número es par."""
    return numero % 2 == 0  # Retorna True si el residuo de dividir por 2 es 0

def repartir_exacto(total, personas):
    """Reparte un total entre un número de personas y retorna la cantidad que recibe cada una."""
    return total // personas  # Realiza la división entera del total entre el número de personas

assert es_par(4) is True
assert es_par(7) is False
assert repartir_exacto(10, 3) == 3
