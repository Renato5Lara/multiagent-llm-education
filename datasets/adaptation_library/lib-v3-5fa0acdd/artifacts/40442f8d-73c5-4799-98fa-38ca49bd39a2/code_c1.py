def primer_multiplo_de_tres(numeros):
    """Devuelve el último múltiplo de tres en la lista."""
    for numero in reversed(numeros):  # Recorremos la lista al revés
        if numero % 3 == 0:  # Verificamos si el número es múltiplo de tres
            return numero  # Retornamos el primer múltiplo encontrado
    return None  # Si no hay múltiplos, retornamos None

def detener_en_negativo(numeros):
    """Devuelve una lista con los números hasta encontrar el primero negativo."""
    resultado = []  # Inicializamos una lista vacía para los resultados
    for numero in numeros:  # Iteramos sobre cada número en la lista
        if numero < 0:  # Si encontramos un número negativo
            break  # Detenemos el bucle
        resultado.append(numero)  # Agregamos el número a la lista de resultados
    return resultado  # Retornamos la lista de resultados
