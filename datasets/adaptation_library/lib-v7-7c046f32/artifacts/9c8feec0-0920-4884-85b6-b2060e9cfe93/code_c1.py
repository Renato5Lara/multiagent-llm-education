def calcular_iva(precio):
    """Calcula el IVA del precio dado."""
    iva = precio * 0.18  # Calcula el 18% del precio
    return iva  # Devuelve el valor del IVA

total = calcular_iva(100)
