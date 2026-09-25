def clasificar_estudiante(nota, asistencia):
    """
    Clasifica el estado de un estudiante basado en su nota y asistencia.
    
    Parámetros:
    nota (int): La nota del estudiante.
    asistencia (int): El porcentaje de asistencia del estudiante.
    
    Retorna:
    str: El estado del estudiante ("aprobado", "aprobado sin certificado" o "desaprobado").
    """
    
    # Verificar si la nota o la asistencia son valores extremos o inválidos
    if nota < 0 or asistencia < 0:
        return "entrada inválida"
    
    # Clasificación del estudiante según la nota
    if nota >= 10:  # Nota mínima para aprobar
        if asistencia >= 75:  # Asistencia mínima para obtener certificado
            return "aprobado"
        else:
            return "aprobado sin certificado"
    else:
        return "desaprobado"

def ejemplo_uso():
    # Ejemplos de uso de la función clasificar_estudiante
    print(clasificar_estudiante(15, 80))  # Debería retornar "aprobado"
    print(clasificar_estudiante(15, 50))  # Debería retornar "aprobado sin certificado"
    print(clasificar_estudiante(8, 90))   # Debería retornar "desaprobado"
