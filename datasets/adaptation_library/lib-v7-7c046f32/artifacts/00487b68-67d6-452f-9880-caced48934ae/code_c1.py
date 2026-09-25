def es_par(numero):
    """Determina si un número es par."""
    # Un número es par si el residuo de dividirlo entre 2 es 0
    return numero % 2 == 0

def repartir_exacto(total, personas):
    """Calcula cuántas personas pueden recibir una parte exacta del total."""
    # La división entera nos da el número de partes exactas que se pueden repartir
    return total // personas
