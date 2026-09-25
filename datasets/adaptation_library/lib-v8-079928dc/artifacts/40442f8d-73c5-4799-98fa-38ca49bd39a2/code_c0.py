def primer_multiplo_de_tres(numeros):
    for numero in numeros:
        if numero % 3 != 0:
            continue
        return numero

def detener_en_negativo(numeros):
    resultado = []
    for numero in numeros:
        if numero < 0:
            break
        resultado.append(numero)
    return resultado
