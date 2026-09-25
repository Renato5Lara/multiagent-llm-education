def sumar_lista(numeros):
    """
    Suma los elementos de una lista de números.

    Parámetros:
    numeros (list): Lista de números a sumar.

    Retorna:
    int: La suma de los números en la lista. Si la lista está vacía, retorna 0.
    """
    total = 0  # Inicializa el total en 0
    for numero in numeros:  # Itera sobre cada número en la lista
        total += numero  # Suma el número actual al total
        print(f'total: {total}')  # Traza el valor de total en cada vuelta
    return total  # Retorna la suma total

def ejemplo_uso():
    """
    Ejemplo de uso de la función sumar_lista.
    """
    resultado = sumar_lista([1, 2, 3])  # Llama a la función con una lista de ejemplo
    print(f'La suma de la lista es: {resultado}')  # Imprime el resultado de la suma

# Estado inicial a nivel de módulo
# assert sumar_lista([1, 2, 3]) == 6
