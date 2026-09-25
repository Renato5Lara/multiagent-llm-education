def describir_tipo(valor):
    """
    Esta función recibe un valor y devuelve una cadena que representa el tipo de dato de ese valor.
    
    Parámetros:
    valor: El valor cuyo tipo se desea determinar.
    
    Retorna:
    str: Una cadena que indica el tipo de dato del valor.
    """
    # Verificamos el tipo de dato usando la función type()
    tipo = type(valor)
    
    # Devolvemos el nombre del tipo como una cadena
    if tipo == int:
        return "int"
    elif tipo == float:
        return "float"
    elif tipo == str:
        return "str"
    elif tipo == bool:
        return "bool"
    else:
        return "tipo desconocido"  # Para manejar tipos no considerados

def ejemplo_uso():
    # Ejemplos de uso de la función describir_tipo
    print(describir_tipo(5))        # Debe imprimir "int"
    print(describir_tipo(5.0))      # Debe imprimir "float"
    print(describir_tipo("cinco"))  # Debe imprimir "str"
    print(describir_tipo(True))      # Debe imprimir "bool"
    print(describir_tipo([]))        # Debe imprimir "tipo desconocido"

assert describir_tipo(5) == "int"
assert describir_tipo(5.0) == "float"
assert describir_tipo("cinco") == "str"
assert describir_tipo(True) == "bool"
