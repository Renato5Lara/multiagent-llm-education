def describir_tipo(valor):
    """Clasifica el tipo de dato primitivo de un valor dado."""
    # Se utiliza la función type() para obtener el tipo del valor
    tipo = type(valor)
    # Se devuelve el nombre del tipo como una cadena
    return tipo.__name__
