def primer_multiplo_de_tres(numeros):
    """
    Devuelve el primer número múltiplo de tres en la lista de números.
    Si se encuentra un múltiplo de tres, se termina el bucle.
    """
    for numero in numeros:
        # Verifica si el número es múltiplo de tres
        if numero % 3 == 0:
            return numero  # Termina el bucle y devuelve el número
        # Si no es múltiplo de tres, continúa con el siguiente número
        continue

def detener_en_negativo(numeros):
    """
    Devuelve una lista de números hasta encontrar un número negativo.
    Si se encuentra un número negativo, se termina el bucle.
    """
    resultado = []
    for numero in numeros:
        # Verifica si el número es negativo
        if numero < 0:
            break  # Termina el bucle si el número es negativo
        resultado.append(numero)  # Agrega el número a la lista de resultados
    return resultado
