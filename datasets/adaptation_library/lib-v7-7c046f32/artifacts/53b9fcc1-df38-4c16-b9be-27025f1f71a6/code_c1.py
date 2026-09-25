contador_global = 0

def incrementar_local():
    """Incrementa un contador local y lo devuelve."""
    contador_local = 0  # Se define un contador local
    contador_local += 1  # Se incrementa el contador local
    contador_local += 1  # Se incrementa nuevamente
    return contador_local  # Se devuelve el valor del contador local

def incrementar_global():
    """Incrementa un contador global y lo devuelve."""
    global contador_global  # Se indica que se usará la variable global
    contador_global += 1  # Se incrementa el contador global
    return contador_global  # Se devuelve el valor del contador global
