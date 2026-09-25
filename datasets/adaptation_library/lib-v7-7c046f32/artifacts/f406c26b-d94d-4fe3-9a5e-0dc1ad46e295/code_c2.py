def actualizar_saldo(saldo_inicial, deposito):
    """
    Actualiza el saldo inicial sumando un depósito.

    Parámetros:
    saldo_inicial (float): El saldo inicial de la cuenta.
    deposito (float): La cantidad de dinero a depositar.

    Retorna:
    float: El nuevo saldo después de realizar el depósito.
    """
    # Verificamos que el saldo inicial y el depósito no sean negativos
    if saldo_inicial < 0:
        raise ValueError("El saldo inicial no puede ser negativo.")
    if deposito < 0:
        raise ValueError("El depósito no puede ser negativo.")
    
    # Calculamos el nuevo saldo
    nuevo_saldo = saldo_inicial + deposito
    
    # Retornamos el nuevo saldo
    return nuevo_saldo

def ejemplo_uso():
    # Ejemplo de uso de la función actualizar_saldo
    saldo = 100  # Saldo inicial
    deposito = 50  # Monto a depositar
    nuevo_saldo = actualizar_saldo(saldo, deposito)  # Actualizamos el saldo
    print(f"Saldo inicial: {saldo}, Depósito: {deposito}, Nuevo saldo: {nuevo_saldo}")

assert actualizar_saldo(100, 50) == 150
