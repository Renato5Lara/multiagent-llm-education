def crear_lista_de_notas():
    """
    Crea una lista de notas predefinidas.
    
    Retorna:
        list: Una lista que contiene las notas [12, 15, 18, 9].
    """
    # Inicializamos la lista de notas
    lista_notas = []
    
    # Agregamos las notas a la lista
    lista_notas.append(12)  # Agregamos la primera nota
    lista_notas.append(15)  # Agregamos la segunda nota
    lista_notas.append(18)  # Agregamos la tercera nota
    lista_notas.append(9)   # Agregamos la cuarta nota
    
    # Retornamos la lista de notas
    return lista_notas

def ejemplo_uso():
    """
    Función que ilustra el uso de la función crear_lista_de_notas.
    """
    # Llamamos a la función y almacenamos el resultado
    notas = crear_lista_de_notas()
    
    # Imprimimos la lista de notas
    print("La lista de notas es:", notas)

assert crear_lista_de_notas() == [12, 15, 18, 9]
