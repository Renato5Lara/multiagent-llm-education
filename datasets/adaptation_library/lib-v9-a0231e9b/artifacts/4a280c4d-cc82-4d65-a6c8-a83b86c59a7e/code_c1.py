def dividir_con_resto(a, b):
    """Devuelve el cociente y el resto de la división de a entre b."""
    cociente = a // b  # Calcula el cociente de la división entera
    resto = a % b      # Calcula el resto de la división
    return (cociente, resto)  # Retorna una tupla con cociente y resto
