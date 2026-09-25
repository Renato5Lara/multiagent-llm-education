def primer_multiplo_de_tres(numeros):
    """
    Encuentra el primer múltiplo de tres en la lista de números.
    
    Parámetros:
    numeros (list): Lista de enteros a evaluar.
    
    Retorna:
    int: El primer múltiplo de tres encontrado, o el último número de la lista si no hay múltiplos de tres.
    """
    # Verificamos si la lista está vacía
    if not numeros:
        return None  # Retornamos None si la lista está vacía
    
    # Iteramos sobre cada número en la lista
    for numero in numeros:
        # Comprobamos si el número es un múltiplo de tres
        if numero % 3 == 0:
            return numero  # Retornamos el primer múltiplo de tres encontrado
    
    # Si no se encontró ningún múltiplo de tres, retornamos el último número de la lista
    return numeros[-1]


def detener_en_negativo(numeros):
    """
    Filtra la lista de números y detiene la iteración al encontrar un número negativo.
    
    Parámetros:
    numeros (list): Lista de enteros a evaluar.
    
    Retorna:
    list: Nueva lista con los números hasta el primer negativo encontrado.
    """
    # Verificamos si la lista está vacía
    if not numeros:
        return []  # Retornamos una lista vacía si la lista original está vacía
    
    resultado = []  # Inicializamos una lista para almacenar los resultados
    
    # Iteramos sobre cada número en la lista
    for numero in numeros:
        # Comprobamos si el número es negativo
        if numero < 0:
            break  # Detenemos la iteración si encontramos un número negativo
        resultado.append(numero)  # Agregamos el número a la lista de resultados
    
    return resultado  # Retornamos la lista de resultados


def ejemplo_uso():
    print(primer_multiplo_de_tres([1, 2, 4, 9]))  # Debería imprimir 9
    print(detener_en_negativo([1, 2, -1, 3]))  # Debería imprimir [1, 2]
