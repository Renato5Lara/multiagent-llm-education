def actualizar_lista(lista):
    """Actualiza la lista mediante operaciones de modificación de tamaño."""
    
    # Se añade el número 40 al final de la lista
    lista.append(40)
    # Traza el contenido de la lista
    print(lista)  # [10, 20, 30, 40]
    
    # Se inserta el número 5 al inicio de la lista
    lista.insert(0, 5)
    # Traza el contenido de la lista
    print(lista)  # [5, 10, 20, 30, 40]
    
    # Se elimina el número 20 de la lista
    lista.remove(20)
    # Traza el contenido de la lista
    print(lista)  # [5, 10, 30, 40]
    
    # Se elimina el último elemento de la lista
    lista.pop()
    # Traza el contenido de la lista
    print(lista)  # [5, 10, 30]
    
    return lista  # Se devuelve la lista final

assert actualizar_lista([10, 20, 30]) == [5, 10, 30]
