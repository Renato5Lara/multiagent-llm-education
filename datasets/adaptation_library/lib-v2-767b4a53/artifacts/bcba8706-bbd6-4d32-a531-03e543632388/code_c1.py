def clasificar_estudiante(nota, asistencia):
    """Clasifica el estado del estudiante según su nota y asistencia."""
    
    # Verificamos si la nota es mayor o igual a 10
    if nota >= 10:
        # Si la asistencia es mayor o igual a 75, el estudiante está aprobado
        if asistencia >= 75:
            return "aprobado"
        else:  # Si la asistencia es menor a 75, no recibe certificado
            return "aprobado sin certificado"
    else:  # Si la nota es menor a 10, el estudiante está desaprobado
        return "desaprobado"
