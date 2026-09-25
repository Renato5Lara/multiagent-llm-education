def buscar_estudiante(lista, nombre):
    """
    Busca el nombre de un estudiante en una lista y devuelve su índice.
    
    Parámetros:
    lista (list): Lista de nombres de estudiantes.
    nombre (str): Nombre del estudiante a buscar.
    
    Retorna:
    int: El índice del estudiante en la lista si se encuentra, 
         o -1 si no se encuentra.
    """
    # Verificamos si la lista está vacía
    if not lista:
        return -1  # Retornamos -1 si la lista está vacía
    
    # Verificamos si el nombre está en la lista
    if nombre in lista:
        # Si el nombre está, usamos .index() para obtener su índice
        return lista.index(nombre)
    else:
        # Si el nombre no está, retornamos -1
        return -1

def ejemplo_uso():
    # Ejemplo de uso de la función buscar_estudiante
    estudiantes = ["Ana", "Luis", "Pedro"]
    print(buscar_estudiante(estudiantes, "Luis"))  # Debería imprimir 1
    print(buscar_estudiante(estudiantes, "Marco"))  # Debería imprimir -1
    print(buscar_estudiante([], "Ana"))  # Debería imprimir -1
    print(buscar_estudiante(["Juan"], "Juan"))  # Debería imprimir 0
    print(buscar_estudiante(["Juan"], "Pedro"))  # Debería imprimir -1
