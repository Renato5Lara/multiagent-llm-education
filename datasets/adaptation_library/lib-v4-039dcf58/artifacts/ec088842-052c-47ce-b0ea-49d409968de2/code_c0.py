def ejecutar_instrucciones(instrucciones):
    total = 0
    for instruccion in instrucciones:
        if instruccion == "sumar1":
            total += 1
        elif instruccion == "duplicar":
            total *= 2
    return total
