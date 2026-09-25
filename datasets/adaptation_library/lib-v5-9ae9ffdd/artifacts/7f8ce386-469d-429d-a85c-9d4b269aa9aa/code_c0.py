def buscar_estudiante(lista, nombre):
    if nombre in lista:
        return lista.index(nombre)
    return -1
