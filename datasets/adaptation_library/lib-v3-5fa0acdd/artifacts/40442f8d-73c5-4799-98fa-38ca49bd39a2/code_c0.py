def primer_multiplo_de_tres(numeros):
    for num in numeros:
        if num % 3 == 0:
            return num
    return None

def detener_en_negativo(numeros):
    resultado = []
    for num in numeros:
        if num < 0:
            break
        resultado.append(num)
    return resultado
