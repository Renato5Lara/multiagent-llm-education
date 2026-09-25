def describir_tipo(valor):
    """Devuelve el tipo de dato del valor proporcionado como una cadena."""
    # Se utiliza la función type() para obtener el tipo del valor
    tipo = type(valor)
    # Se convierte el tipo a cadena y se extrae solo el nombre del tipo
    return tipo.__name__  # Devuelve el nombre del tipo como una cadena

assert describir_tipo(5) == "int"
assert describir_tipo(5.0) == "float"
assert describir_tipo("cinco") == "str"
assert describir_tipo(True) == "bool"
