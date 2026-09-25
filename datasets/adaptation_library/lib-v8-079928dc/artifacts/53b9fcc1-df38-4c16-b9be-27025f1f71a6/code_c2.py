contador_global = 0

def incrementar_local():
    """Incrementa un contador local y lo devuelve.
    
    Este contador se reinicia en cada llamada a la función.
    """
    contador_local = 1  # Inicializa el contador local
    contador_local += 1  # Incrementa el contador local
    return contador_local  # Devuelve el valor del contador local

def incrementar_global():
    """Incrementa un contador global y lo devuelve.
    
    Este contador persiste entre llamadas a la función.
    """
    global contador_global  # Indica que se usará la variable global
    contador_global += 1  # Incrementa el contador global
    return contador_global  # Devuelve el valor del contador global

def ejemplo_uso():
    """Ejemplo de uso de las funciones incrementar_local e incrementar_global."""
    print(incrementar_local())  # Debería imprimir 2
    print(incrementar_global())  # Debería imprimir 1
    print(incrementar_global())  # Debería imprimir 2
