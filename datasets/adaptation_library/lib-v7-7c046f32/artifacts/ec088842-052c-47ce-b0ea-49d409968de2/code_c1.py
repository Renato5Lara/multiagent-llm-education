def ejecutar_instrucciones(instrucciones):
    """Ejecuta una lista de instrucciones y devuelve el resultado final."""
    resultado = 0  # Inicializa el resultado en 0
    
    for instruccion in instrucciones:  # Itera sobre cada instrucción
        if instruccion == "sumar1":  # Si la instrucción es sumar1
            resultado += 1  # Suma 1 al resultado
        elif instruccion == "duplicar":  # Si la instrucción es duplicar
            resultado *= 2  # Duplica el resultado
    
    return resultado  # Devuelve el resultado final
