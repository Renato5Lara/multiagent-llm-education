def dividir_con_resto(a, b):
    """
    Divide dos números y retorna el cociente y el resto.

    Parámetros:
    a (int): El numerador.
    b (int): El denominador.

    Retorna:
    tuple: Un tuple que contiene el cociente y el resto de la división.
    """
    # Manejo de caso límite: si el denominador es cero
    if b == 0:
        raise ValueError("El denominador no puede ser cero.")
    
    # Cálculo del cociente
    cociente = a // b
    
    # Cálculo del resto
    resto = a % b
    
    # Retorno del resultado como un tuple
    return (cociente, resto)

def ejemplo_uso():
    # Ejemplo de uso de la función dividir_con_resto
    resultado = dividir_con_resto(10, 3)
    print(f"Dividir 10 entre 3 da: Cociente = {resultado[0]}, Resto = {resultado[1]}")

assert dividir_con_resto(10, 3) == (3, 1)
