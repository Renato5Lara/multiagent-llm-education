def puede_matricularse(tiene_requisitos, sin_deuda):
    """Determina si un estudiante puede matricularse basado en requisitos y deudas."""
    # Retorna True si tiene los requisitos y no tiene deudas
    return tiene_requisitos and sin_deuda

assert puede_matricularse(True, True) is True
assert puede_matricularse(True, False) is False
