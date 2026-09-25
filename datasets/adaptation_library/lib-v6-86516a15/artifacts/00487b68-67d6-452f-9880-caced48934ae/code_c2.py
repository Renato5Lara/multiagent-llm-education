def es_par(numero):
    """
    Determina si un número es par.

    Un número es par si es divisible por 2 sin residuo.

    Parámetros:
    numero (int): El número a evaluar.

    Retorna:
    bool: True si el número es par, False si es impar.
    """
    # Verificamos si el número es divisible por 2
    return numero % 2 == 0

def repartir_exacto(total, personas):
    """
    Calcula cuántas personas pueden recibir una parte exacta de un total.

    Realiza la división entera del total entre el número de personas.

    Parámetros:
    total (int): La cantidad total a repartir.
    personas (int): El número de personas entre las que se reparte.

    Retorna:
    int: La cantidad entera que recibe cada persona.
    """
    # Verificamos si el número de personas es cero para evitar división por cero
    if personas == 0:
        return 0  # No se puede repartir entre cero personas
    # Realizamos la división entera
    return total // personas

def ejemplo_uso():
    print(es_par(4))  # Debería imprimir True
    print(es_par(7))  # Debería imprimir False
    print(repartir_exacto(10, 3))  # Debería imprimir 3
    print(repartir_exacto(10, 0))  # Debería imprimir 0
