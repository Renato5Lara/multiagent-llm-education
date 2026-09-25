def dividir_con_resto(a, b):
    """
    Divide dos números y retorna el cociente y el resto.

    Parámetros:
    a (int): El numerador.
    b (int): El denominador.

    Retorna:
    tuple: Una tupla que contiene el cociente y el resto de la división.
    """
    # Manejo de caso límite: si el denominador es cero
    if b == 0:
        raise ValueError("El denominador no puede ser cero.")
    
    # Cálculo del cociente
    cociente = a // b
    
    # Cálculo del resto
    resto = a % b
    
    # Retorno de una tupla con el cociente y el resto
    return cociente, resto

def ejemplo_uso():
    # Ejemplo de uso de la función dividir_con_resto
    resultado = dividir_con_resto(10, 3)
    print(f"El cociente y resto de 10 dividido por 3 son: {resultado}")
