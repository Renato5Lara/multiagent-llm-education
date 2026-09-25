def encontrar_mayor(numeros):
    mayor = numeros[0]
    for num in numeros:
        if num > mayor:
            mayor = num
    return mayor
