def procesar_promedio(notas):
    """
    Calcula el promedio de una lista de notas.

    Parámetros:
    notas (list): Lista de números que representan las notas.

    Retorna:
    float: El promedio de las notas. Si la lista está vacía, retorna 0.
    """
    # Verificamos si la lista de notas está vacía
    if not notas:
        return 0  # Retornamos 0 si no hay notas

    # Sumar todas las notas
    suma_notas = sum(notas)  # Suma de las notas
    # Contar la cantidad de notas
    cantidad_notas = len(notas)  # Número de notas

    # Calcular el promedio
    promedio = suma_notas / cantidad_notas  # Promedio de las notas
    return promedio  # Retornamos el promedio calculado

def ejemplo_uso():
    """
    Función que ilustra el uso de la función procesar_promedio.
    """
    # Ejemplo de uso con una lista de notas
    notas = [10, 20, 30]
    promedio = procesar_promedio(notas)  # Llamamos a la función
    print(f"El promedio de las notas {notas} es: {promedio}")  # Mostramos el resultado

assert procesar_promedio([10, 20, 30]) == 20
