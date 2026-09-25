contador_global = 0

def incrementar_local():
    contador_local = 1
    return contador_local + 1

def incrementar_global():
    global contador_global
    contador_global += 1
    return contador_global
