def actualizar_lista(lista):
    """
    Actualiza la lista mediante operaciones de modificación de tamaño.
    
    Args:
        lista (list): La lista inicial que se va a modificar.
    
    Returns:
        list: La lista modificada después de realizar las operaciones.
    """
    # Verificamos si la lista está vacía
    if not lista:
        return lista  # Retornamos la lista vacía si no hay elementos

    # Operación append: añadimos 40 al final de la lista
    lista.append(40)
    # Traza después de append
    print(lista)  # [10, 20, 30, 40]

    # Operación insert: añadimos 5 en la posición 0
    lista.insert(0, 5)
    # Traza después de insert
    print(lista)  # [5, 10, 20, 30, 40]

    # Operación remove: eliminamos el valor 20
    lista.remove(20)
    # Traza después de remove
    print(lista)  # [5, 10, 30, 40]

    # Operación pop: eliminamos el último elemento
    lista.pop()
    # Traza después de pop
    print(lista)  # [5, 10, 30]

    return lista  # Retornamos la lista final

def ejemplo_uso():
    """
    Función que ilustra el uso de la función actualizar_lista.
    """
    resultado = actualizar_lista([10, 20, 30])
    print("Resultado final:", resultado)  # Debería mostrar: Resultado final: [5, 10, 30]
