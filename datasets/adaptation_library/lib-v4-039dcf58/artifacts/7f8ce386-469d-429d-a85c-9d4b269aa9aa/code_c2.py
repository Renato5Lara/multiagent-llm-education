def buscar_estudiante(lista, nombre):
    """
    Busca el índice de un estudiante en una lista.
    
    Parámetros:
    lista (list): Lista de nombres de estudiantes.
    nombre (str): Nombre del estudiante a buscar.
    
    Retorna:
    int: El índice del estudiante en la lista si se encuentra, -1 si no se encuentra.
    """
    # Verificamos si la lista está vacía
    if not lista:
        return -1  # Retornamos -1 si la lista está vacía
    
    # Recorremos la lista para buscar el nombre
    for i in range(len(lista)):
        # Comparamos el nombre actual con el nombre buscado
        if lista[i] == nombre:
            return i  # Retornamos el índice si encontramos el nombre
    
    return -1  # Retornamos -1 si no encontramos el nombre

def ejemplo_uso():
    # Ejemplo de uso de la función buscar_estudiante
    estudiantes = ["Ana", "Luis", "Pedro"]
    print(buscar_estudiante(estudiantes, "Luis"))  # Debería imprimir 1
    print(buscar_estudiante(estudiantes, "Marco"))  # Debería imprimir -1
    print(buscar_estudiante([], "Ana"))  # Debería imprimir -1
    print(buscar_estudiante(["Juan"], "Juan"))  # Debería imprimir 0

assert buscar_estudiante(["Ana", "Luis"], "Luis") == 1
assert buscar_estudiante(["Ana", "Luis"], "Marco") == -1
