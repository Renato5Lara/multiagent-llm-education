def actualizar_saldo(saldo_inicial, deposito):
    """
    Actualiza el saldo inicial sumando un depósito.
    
    Parámetros:
    saldo_inicial (float): El saldo inicial de la cuenta.
    deposito (float): La cantidad de dinero a depositar.
    
    Retorna:
    float: El nuevo saldo después de realizar el depósito.
    """
    # Verificamos si el saldo inicial es un número válido
    if saldo_inicial is None or deposito is None:
        return "Error: saldo inicial o depósito no pueden ser None"
    
    # Verificamos si el saldo inicial y el depósito son números
    if not isinstance(saldo_inicial, (int, float)) or not isinstance(deposito, (int, float)):
        return "Error: saldo inicial y depósito deben ser números"
    
    # Verificamos si el saldo inicial es negativo
    if saldo_inicial < 0:
        return "Error: saldo inicial no puede ser negativo"
    
    # Verificamos si el depósito es negativo
    if deposito < 0:
        return "Error: el depósito no puede ser negativo"
    
    # Antes de la suma
    saldo = saldo_inicial
    # Aquí el saldo es igual a saldo_inicial
    # Ahora sumamos el depósito al saldo
    saldo += deposito
    # Después de la suma
    # Aquí el saldo es igual a saldo_inicial + deposito
    return saldo

def ejemplo_uso():
    saldo_inicial = 100
    deposito = 50
    nuevo_saldo = actualizar_saldo(saldo_inicial, deposito)
    print(f"Saldo inicial: {saldo_inicial}. Después de la suma: {nuevo_saldo}.")
