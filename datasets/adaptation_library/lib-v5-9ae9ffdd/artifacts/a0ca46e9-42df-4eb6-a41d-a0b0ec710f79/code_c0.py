def actualizar_lista(lista):
    lista.append(40)
    lista.insert(0, 5)
    lista.remove(20)
    lista.pop()
    return lista

assert actualizar_lista([10, 20, 30]) == [5, 10, 30]
