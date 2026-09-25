def aprobo(nota):
    """Determina si una nota es suficiente para aprobar."""
    # Se considera que se aprueba con una nota mayor o igual a 11
    return nota >= 11  # Devuelve True si la nota es 11 o más, False en caso contrario

assert aprobo(11) is True
assert aprobo(10) is False
