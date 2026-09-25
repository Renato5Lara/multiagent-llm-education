def clasificar_estudiante(nota, asistencia):
    if nota >= 10:
        if asistencia >= 75:
            return "aprobado"
        else:
            return "aprobado sin certificado"
    else:
        return "desaprobado"
