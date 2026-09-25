def ejecutar_instrucciones(instrucciones):
    """
    Ejecuta una lista de instrucciones y devuelve el resultado final.
    
    Las instrucciones pueden ser:
    - "sumar1": suma 1 al resultado actual.
    - "duplicar": duplica el resultado actual.
    
    Parámetros:
    instrucciones (list): Lista de instrucciones a ejecutar.
    
    Retorna:
    int: Resultado final después de ejecutar todas las instrucciones.
    """
    resultado = 0  # Inicializa el resultado en 0
    
    for instruccion in instrucciones:  # Itera sobre cada instrucción
        if instruccion == "sumar1":  # Si la instrucción es sumar1
            resultado += 1  # Suma 1 al resultado
        elif instruccion == "duplicar":  # Si la instrucción es duplicar
            resultado *= 2  # Duplica el resultado
    
    return resultado  # Devuelve el resultado final

def ejemplo_uso():
    instrucciones = ["sumar1", "duplicar", "sumar1"]
    resultado = ejecutar_instrucciones(instrucciones)
    print(f"Resultado de ejecutar las instrucciones {instrucciones}: {resultado}")
