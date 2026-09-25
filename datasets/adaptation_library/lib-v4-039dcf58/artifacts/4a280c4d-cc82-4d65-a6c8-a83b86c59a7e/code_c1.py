def dividir_con_resto(a, b):
    """Dividir dos números y retornar el cociente y el resto."""
    cociente = a // b  # Calcular el cociente de la división entera
    resto = a % b      # Calcular el resto de la división
    return (cociente, resto)  # Retornar ambos valores como una tupla

assert dividir_con_resto(10, 3) == (3, 1)
