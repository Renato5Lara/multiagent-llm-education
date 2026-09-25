def primer_multiplo_de_tres(numeros):
    """
    Devuelve el primer número múltiplo de tres en la lista de números.
    Si no hay múltiplos de tres, devuelve None.
    
    :param numeros: Lista de números enteros.
    :return: El primer múltiplo de tres encontrado o None si no hay.
    """
    for numero in numeros:
        # Si el número es múltiplo de tres, lo devolvemos
        if numero % 3 == 0:
            return numero
        # Si no es múltiplo de tres, continuamos con el siguiente número
        continue
    # Si no encontramos ningún múltiplo de tres, devolvemos None
    return None

def detener_en_negativo(numeros):
    """
    Devuelve una lista de números hasta encontrar un número negativo.
    El bucle se detiene al encontrar el primer número negativo.
    
    :param numeros: Lista de números enteros.
    :return: Lista de números hasta el primer negativo (excluido).
    """
    resultado = []
    for numero in numeros:
        # Si encontramos un número negativo, rompemos el bucle
        if numero < 0:
            break
        # Si el número no es negativo, lo añadimos a la lista de resultados
        resultado.append(numero)
    return resultado

def ejemplo_uso():
    """
    Ejemplo de uso de las funciones primer_multiplo_de_tres y detener_en_negativo.
    """
    # Ejemplo de uso de primer_multiplo_de_tres
    lista1 = [1, 2, 4, 9]
    multiplo = primer_multiplo_de_tres(lista1)
    print(f"El primer múltiplo de tres en {lista1} es {multiplo}")

    # Ejemplo de uso de detener_en_negativo
    lista2 = [1, 2, -1, 3]
    resultado = detener_en_negativo(lista2)
    print(f"Los números antes del primer negativo en {lista2} son {resultado}")
