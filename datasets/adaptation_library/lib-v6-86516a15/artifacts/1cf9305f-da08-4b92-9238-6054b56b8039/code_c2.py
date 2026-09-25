def procesar_promedio(notas):
    """
    Calcula el promedio de una lista de notas.

    Parámetros:
    notas (list): Lista de números que representan las notas.

    Retorna:
    float: El promedio de las notas. Si la lista está vacía, retorna 0.
    """
    # Paso 1: Verificar si la lista de notas está vacía
    if not notas:
        return 0  # Si está vacía, retornar 0

    # Paso 2: Calcular la suma de las notas
    suma_notas = sum(notas)  # Sumar todas las notas

    # Paso 3: Calcular el promedio dividiendo la suma entre la cantidad de notas
    promedio = suma_notas / len(notas)  # Dividir la suma por el número de notas
    return promedio  # Retornar el promedio calculado

def ejemplo_uso():
    print(procesar_promedio([10, 20, 30]))  # Ejemplo de uso de la función procesar_promedio
