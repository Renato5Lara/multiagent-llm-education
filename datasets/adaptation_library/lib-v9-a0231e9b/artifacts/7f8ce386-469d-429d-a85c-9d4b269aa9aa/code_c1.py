def buscar_estudiante(lista, nombre):
    """Busca el nombre de un estudiante en la lista y devuelve su índice o -1 si no está."""
    if nombre in lista:  # Verifica si el nombre está en la lista
        return lista.index(nombre)  # Devuelve el índice del nombre
    else:
        return -1  # Devuelve -1 si el nombre no está en la lista
