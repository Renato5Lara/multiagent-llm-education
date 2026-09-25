def crear_lista_de_notas():
    """
    Crea una lista de notas predefinidas.
    
    Returns:
        list: Una lista que contiene las notas [12, 15, 18, 9].
    """
    # Definimos la lista de notas
    notas = [12, 15, 18, 9]
    
    # Retornamos la lista de notas
    return notas

def ejemplo_uso():
    """
    Función que ilustra el uso de la función crear_lista_de_notas.
    """
    # Llamamos a la función y almacenamos el resultado
    lista_notas = crear_lista_de_notas()
    
    # Imprimimos la lista de notas
    print("La lista de notas es:", lista_notas)

assert crear_lista_de_notas() == [12, 15, 18, 9]
