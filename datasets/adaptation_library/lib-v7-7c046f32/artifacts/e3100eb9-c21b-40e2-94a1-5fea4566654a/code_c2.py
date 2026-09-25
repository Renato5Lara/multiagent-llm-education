def puede_matricularse(tiene_requisitos, sin_deuda):
    """
    Determina si un estudiante puede matricularse en función de dos condiciones:
    1. Si tiene los requisitos necesarios.
    2. Si no tiene deudas pendientes.

    Ambas condiciones deben ser verdaderas para que el estudiante pueda matricularse.

    :param tiene_requisitos: bool, indica si el estudiante tiene los requisitos.
    :param sin_deuda: bool, indica si el estudiante no tiene deudas.
    :return: bool, True si puede matricularse, False en caso contrario.
    """
    # Se evalúan ambas condiciones usando el operador lógico and
    return tiene_requisitos and sin_deuda

def ejemplo_uso():
    # Ejemplo de uso de la función puede_matricularse
    print(puede_matricularse(True, True))   # Debería imprimir True
    print(puede_matricularse(True, False))  # Debería imprimir False
    print(puede_matricularse(False, True))  # Debería imprimir False
    print(puede_matricularse(False, False)) # Debería imprimir False
