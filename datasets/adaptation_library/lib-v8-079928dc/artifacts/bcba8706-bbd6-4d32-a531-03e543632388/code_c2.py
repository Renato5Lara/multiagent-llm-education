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
    if nota >= 10:  # Si la nota es mayor o igual a 10
        if asistencia >= 75:  # Si la asistencia es mayor o igual a 75%
            return "aprobado"  # Estudiante aprobado
        else:  # Si la asistencia es menor a 75%
            return "aprobado sin certificado"  # Estudiante aprobado sin certificado
    else:  # Si la nota es menor a 10
        return "desaprobado"  # Estudiante desaprobado

def ejemplo_uso():
    print(clasificar_estudiante(15, 80))  # Debe imprimir "aprobado"
    print(clasificar_estudiante(15, 50))  # Debe imprimir "aprobado sin certificado"
    print(clasificar_estudiante(8, 90))   # Debe imprimir "desaprobado"
