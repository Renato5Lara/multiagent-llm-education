def actualizar_saldo(saldo_inicial, deposito):
    """Actualiza el saldo inicial sumando un depósito."""
    # Sumar el depósito al saldo inicial
    nuevo_saldo = saldo_inicial + deposito
    # Retornar el nuevo saldo
    return nuevo_saldo

assert actualizar_saldo(100, 50) == 150
