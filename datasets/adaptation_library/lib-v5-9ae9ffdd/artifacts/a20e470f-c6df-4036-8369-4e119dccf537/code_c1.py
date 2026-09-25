def convertir_a_numero(texto):
    """Convierte una cadena de texto a un número entero o decimal."""
    # Intenta convertir el texto a un número entero
    try:
        return int(texto)  # Si tiene éxito, devuelve el número entero
    except ValueError:
        # Si falla, intenta convertir el texto a un número decimal
        return float(texto)  # Devuelve el número decimal si tiene éxito

assert convertir_a_numero("10") == 10
assert convertir_a_numero("3.5") == 3.5
