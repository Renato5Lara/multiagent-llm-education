def obtener_primero_y_ultimo(lista):
    """
    Obtiene el primer y el último elemento de una lista.

    Parámetros:
    lista (list): La lista de la cual se extraerán los elementos.

    Retorna:
    tuple: Un tuple que contiene el primer y el último elemento de la lista.
           Si la lista está vacía, retorna (None, None).
    """
    # Verificamos si la lista está vacía
    if not lista:
        return (None, None)  # Retornamos None para ambos elementos si la lista está vacía
    
    # Obtenemos el primer elemento
    primero = lista[0]
    # Obtenemos el último elemento
    ultimo = lista[-1]
    
    # Retornamos ambos elementos como un tuple
    return (primero, ultimo)

def ejemplo_uso():
    # Ejemplo de uso de la función
    print(obtener_primero_y_ultimo([10, 20, 30]))  # Debería imprimir (10, 30)
    print(obtener_primero_y_ultimo([]))             # Debería imprimir (None, None)
    print(obtener_primero_y_ultimo([5]))            # Debería imprimir (5, 5)
    print(obtener_primero_y_ultimo([1, 2, 3, 4, 5]))  # Debería imprimir (1, 5)

assert obtener_primero_y_ultimo([10, 20, 30]) == (10, 30)
