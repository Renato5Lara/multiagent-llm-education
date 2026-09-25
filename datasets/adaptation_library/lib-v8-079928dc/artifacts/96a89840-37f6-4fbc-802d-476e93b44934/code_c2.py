def obtener_primeros_tres(lista):
    """
    Obtiene los primeros tres elementos de una lista.

    Parámetros:
    lista (list): La lista de la cual se extraerán los primeros tres elementos.

    Retorna:
    list: Una lista con los primeros tres elementos. Si la lista tiene menos de tres elementos,
    se devolverá la lista completa.
    """
    # Verificamos si la lista está vacía
    if not lista:
        return []
    
    # Devolvemos los primeros tres elementos usando slicing
    return lista[:3]

def ejemplo_uso():
    # Ejemplo de uso de la función obtener_primeros_tres
    print(obtener_primeros_tres([1, 2, 3, 4, 5]))  # Debería imprimir [1, 2, 3]
    print(obtener_primeros_tres([10, 20]))          # Debería imprimir [10, 20]
    print(obtener_primeros_tres([]))                # Debería imprimir []
    print(obtener_primeros_tres([100]))             # Debería imprimir [100]
    print(obtener_primeros_tres([1, 2, 3, 4, 5, 6]))  # Debería imprimir [1, 2, 3]
