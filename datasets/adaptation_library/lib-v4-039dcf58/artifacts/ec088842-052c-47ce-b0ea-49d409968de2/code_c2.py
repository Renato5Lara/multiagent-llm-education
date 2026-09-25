def ejecutar_instrucciones(instrucciones):
    """
    Ejecuta una lista de instrucciones que modifican un valor inicial.
    
    Parámetros:
    instrucciones (list): Lista de instrucciones a ejecutar. Las instrucciones pueden ser:
        - "sumar1": Suma 1 al valor actual.
        - "duplicar": Duplica el valor actual.
    
    Retorna:
    int: El valor final después de ejecutar todas las instrucciones.
    """
    # Valor inicial
    valor = 0
    
    # Verificar si la lista de instrucciones está vacía
    if not instrucciones:
        return valor  # Retorna 0 si no hay instrucciones
    
    # Iterar sobre cada instrucción en la lista
    for instruccion in instrucciones:
        if instruccion == "sumar1":
            valor += 1  # Sumar 1 al valor actual
        elif instruccion == "duplicar":
            valor *= 2  # Duplicar el valor actual
        else:
            raise ValueError(f"Instrucción desconocida: {instruccion}")  # Manejo de instrucciones no válidas
    
    return valor  # Retornar el valor final

def ejemplo_uso():
    """
    Ejemplo de uso de la función ejecutar_instrucciones.
    """
    instrucciones = ["sumar1", "sumar1", "duplicar"]
    resultado = ejecutar_instrucciones(instrucciones)
    print(f"Resultado de las instrucciones {instrucciones}: {resultado}")  # Imprimir el resultado

assert ejecutar_instrucciones(["sumar1", "sumar1", "duplicar"]) == 4
