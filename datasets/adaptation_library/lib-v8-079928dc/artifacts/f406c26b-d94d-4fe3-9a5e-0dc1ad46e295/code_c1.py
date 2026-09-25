def actualizar_saldo(saldo_inicial, deposito):
    """
    Actualiza el saldo sumando el depósito al saldo inicial.
    
    Parámetros:
    saldo_inicial -- el saldo antes del depósito
    deposito -- la cantidad a añadir al saldo
    
    Retorna:
    El nuevo saldo después de añadir el depósito.
    """
    # 'saldo' inicialmente tiene el valor de 'saldo_inicial'
    saldo = saldo_inicial
    
    # Se añade 'deposito' al 'saldo'
    saldo += deposito
    
    # Retorna el nuevo valor de 'saldo'
    return saldo
