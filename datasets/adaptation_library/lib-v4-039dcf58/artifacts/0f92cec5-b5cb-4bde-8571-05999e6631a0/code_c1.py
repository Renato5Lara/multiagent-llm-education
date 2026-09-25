def obtener_primero_y_ultimo(lista):
    """Devuelve el primer y último elemento de una lista."""
    primero = lista[0]  # Obtiene el primer elemento de la lista
    ultimo = lista[-1]  # Obtiene el último elemento de la lista
    return (primero, ultimo)  # Retorna una tupla con el primer y último elemento

assert obtener_primero_y_ultimo([10, 20, 30]) == (10, 30)
