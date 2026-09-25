def puede_matricularse(tiene_requisitos, sin_deuda):
    """
    Determina si un estudiante puede matricularse en función de si tiene los requisitos
    necesarios y si no tiene deudas.

    Parámetros:
    tiene_requisitos (bool): Indica si el estudiante cumple con los requisitos.
    sin_deuda (bool): Indica si el estudiante no tiene deudas.

    Retorna:
    bool: True si el estudiante puede matricularse, False en caso contrario.
    """
    # Verificamos que los parámetros sean del tipo esperado
    if not isinstance(tiene_requisitos, bool) or not isinstance(sin_deuda, bool):
        raise ValueError("Ambos parámetros deben ser de tipo booleano.")

    # Si tiene los requisitos y no tiene deudas, puede matricularse
    if tiene_requisitos and sin_deuda:
        return True
    else:
        return False

def ejemplo_uso():
    # Ejemplo de uso de la función puede_matricularse
    print(puede_matricularse(True, True))   # Debería imprimir: True
    print(puede_matricularse(True, False))  # Debería imprimir: False
    print(puede_matricularse(False, True))  # Debería imprimir: False
    print(puede_matricularse(False, False)) # Debería imprimir: False

assert puede_matricularse(True, True) is True
assert puede_matricularse(True, False) is False
