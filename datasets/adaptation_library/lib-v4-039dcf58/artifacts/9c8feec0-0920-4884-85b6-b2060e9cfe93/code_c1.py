def calcular_iva(precio):
    """Calcula el IVA del precio dado."""
    tasa_iva = 0.18  # Definimos la tasa de IVA como 18%
    iva = precio * tasa_iva  # Calculamos el IVA multiplicando el precio por la tasa
    return iva  # Devolvemos el valor del IVA calculado

assert calcular_iva(100) == 18.0
