def crear_lista_de_notas():
    """Crea una lista con 4 notas de estudiantes en el orden en que fueron registradas."""
    # Inicializamos la lista de notas
    notas = []
    
    # Agregamos las notas a la lista
    notas.append(12)  # Primera nota
    notas.append(15)  # Segunda nota
    notas.append(18)  # Tercera nota
    notas.append(9)   # Cuarta nota
    
    # Retornamos la lista de notas
    return notas

def ejemplo_uso():
    """Ejemplo de uso de la función crear_lista_de_notas."""
    # Llamamos a la función y almacenamos el resultado
    lista_de_notas = crear_lista_de_notas()
    
    # Imprimimos la lista de notas
    print(lista_de_notas)  # Debería mostrar: [12, 15, 18, 9]
