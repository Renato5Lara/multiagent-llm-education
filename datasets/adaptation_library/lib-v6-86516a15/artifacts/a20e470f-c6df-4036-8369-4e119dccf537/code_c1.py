def convertir_a_numero(texto):
    """Convierte un texto a un número entero o flotante según su formato."""
    if '.' in texto:  # Verifica si hay un punto decimal en el texto
        return float(texto)  # Convierte a float si hay punto decimal
    else:
        return int(texto)  # Convierte a int si no hay punto decimal
