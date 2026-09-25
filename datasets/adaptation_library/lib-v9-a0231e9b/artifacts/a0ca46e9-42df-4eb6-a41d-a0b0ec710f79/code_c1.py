def actualizar_lista(lista):
    """Actualiza la lista mediante operaciones de modificación de tamaño."""
    
    # Agrega el número 40 al final de la lista
    lista.append(40)  # [10, 20, 30, 40]
    
    # Inserta el número 5 al inicio de la lista
    lista.insert(0, 5)  # [5, 10, 20, 30, 40]
    
    # Elimina el número 20 de la lista
    lista.remove(20)  # [5, 10, 30, 40]
    
    # Elimina el último elemento de la lista
    lista.pop()  # [5, 10, 30]
    
    return lista
