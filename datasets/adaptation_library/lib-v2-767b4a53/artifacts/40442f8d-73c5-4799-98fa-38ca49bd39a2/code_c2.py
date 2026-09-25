def primer_multiplo_de_tres(numeros):
    """
    Devuelve el último número en la lista que es múltiplo de tres.
    
    :param numeros: Lista de números enteros.
    :return: El último múltiplo de tres encontrado en la lista.
    """
    # Inicializamos una variable para almacenar el último múltiplo de tres encontrado
    ultimo_multiplo = None
    
    # Recorremos la lista de números
    for numero in numeros:
        # Verificamos si el número es múltiplo de tres
        if numero % 3 == 0:
            ultimo_multiplo = numero  # Actualizamos el último múltiplo encontrado
    
    # Si no se encontró ningún múltiplo de tres, retornamos None
    return ultimo_multiplo if ultimo_multiplo is not None else None


def detener_en_negativo(numeros):
    """
    Devuelve una lista de números hasta que se encuentra un número negativo.
    
    :param numeros: Lista de números enteros.
    :return: Lista de números hasta el primer número negativo.
    """
    resultado = []  # Lista para almacenar los números hasta el negativo
    
    # Recorremos la lista de números
    for numero in numeros:
        # Si encontramos un número negativo, detenemos el bucle
        if numero < 0:
            break
        resultado.append(numero)  # Agregamos el número a la lista de resultados
    
    return resultado  # Retornamos la lista de resultados


def ejemplo_uso():
    """
    Función que ilustra el uso de las funciones definidas.
    """
    print("Ejemplo de uso de primer_multiplo_de_tres:")
    print(primer_multiplo_de_tres([1, 2, 4, 9]))  # Debería imprimir 9
    
    print("Ejemplo de uso de detener_en_negativo:")
    print(detener_en_negativo([1, 2, -1, 3]))  # Debería imprimir [1, 2]
