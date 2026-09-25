def buscar_estudiante(lista, nombre):
    """Busca el nombre de un estudiante en la lista y devuelve su índice o -1 si no se encuentra."""
    try:
        # Intenta encontrar el índice del nombre en la lista
        return lista.index(nombre)  # Devuelve el índice del nombre
    except ValueError:
        # Si el nombre no se encuentra, se lanza una excepción
        return -1  # Devuelve -1 si el nombre no está en la lista

assert buscar_estudiante(["Ana", "Luis"], "Luis") == 1
assert buscar_estudiante(["Ana", "Luis"], "Marco") == -1
