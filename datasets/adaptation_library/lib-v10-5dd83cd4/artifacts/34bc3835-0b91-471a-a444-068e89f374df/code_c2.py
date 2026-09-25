def describir_tipo(valor):
    """
    Clasifica el tipo de dato primitivo del valor proporcionado.
    
    Parámetros:
    valor: El valor cuyo tipo de dato se desea clasificar.
    
    Retorna:
    str: Una cadena que representa el tipo de dato primitivo del valor.
    """
    # Verificar si el valor es de tipo entero
    if isinstance(valor, int):
        # Caso especial: True y False son instancias de int en Python
        if valor is True or valor is False:
            return "bool"
        return "int"
    # Verificar si el valor es de tipo flotante
    elif isinstance(valor, float):
        return "float"
    # Verificar si el valor es de tipo cadena
    elif isinstance(valor, str):
        return "str"
    # Verificar si el valor es de tipo booleano
    elif isinstance(valor, bool):
        return "bool"
    # Si el tipo de dato no es reconocido, retornar None
    return None

def ejemplo_uso():
    """
    Muestra ejemplos de uso de la función describir_tipo.
    """
    # Ejemplos de uso de la función describir_tipo
    print(describir_tipo(5))      # Debería imprimir "int"
    print(describir_tipo(5.0))    # Debería imprimir "float"
    print(describir_tipo("cinco"))# Debería imprimir "str"
    print(describir_tipo(True))   # Debería imprimir "bool"
