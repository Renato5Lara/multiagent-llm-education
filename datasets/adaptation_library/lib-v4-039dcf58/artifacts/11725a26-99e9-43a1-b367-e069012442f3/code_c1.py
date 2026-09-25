def clasificar_nota(nota):
    """Clasifica la nota en categorías: excelente, regular o insuficiente."""
    
    # Verifica si la nota es mayor o igual a 16
    if nota >= 16:
        return "excelente"  # Retorna "excelente" si la nota es alta
    # Verifica si la nota es mayor o igual a 10
    elif nota >= 10:
        return "regular"  # Retorna "regular" si la nota es aceptable
    else:
        return "insuficiente"  # Retorna "insuficiente" si la nota es baja
