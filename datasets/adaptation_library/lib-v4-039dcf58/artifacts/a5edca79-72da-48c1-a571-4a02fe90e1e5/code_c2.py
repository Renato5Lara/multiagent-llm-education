def formatear_reporte(nombre, nota):
    """
    Formatea un reporte con el nombre del estudiante y su nota.
    
    Parámetros:
    nombre (str): El nombre del estudiante.
    nota (int): La nota del estudiante.
    
    Retorna:
    str: Un string formateado con el nombre y la nota del estudiante.
    """
    # Verificar si el nombre está vacío
    if not nombre:
        nombre = "Nombre no proporcionado"
    
    # Verificar si la nota es un número válido
    if nota < 0:
        nota = 0
    elif nota > 20:
        nota = 20
    
    # Formatear el reporte
    return f"Estudiante: {nombre} - Nota: {nota}"

def ejemplo_uso():
    # Ejemplo de uso de la función formatear_reporte
    print(formatear_reporte("Ana", 18))  # Salida esperada: "Estudiante: Ana - Nota: 18"
    print(formatear_reporte("", 15))      # Salida esperada: "Estudiante: Nombre no proporcionado - Nota: 15"
    print(formatear_reporte("Luis", -5))  # Salida esperada: "Estudiante: Luis - Nota: 0"
    print(formatear_reporte("Marta", 25)) # Salida esperada: "Estudiante: Marta - Nota: 20"
