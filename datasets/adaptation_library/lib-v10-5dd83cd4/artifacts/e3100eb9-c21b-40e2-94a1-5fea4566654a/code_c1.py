def puede_matricularse(tiene_requisitos, sin_deuda):
    """Determina si un estudiante puede matricularse basado en requisitos y deudas."""
    # Ambas condiciones deben ser verdaderas para que el estudiante pueda matricularse
    return tiene_requisitos and sin_deuda  # Retorna True solo si ambas condiciones son True
