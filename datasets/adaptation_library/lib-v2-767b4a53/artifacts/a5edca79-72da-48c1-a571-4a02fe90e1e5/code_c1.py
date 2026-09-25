def formatear_reporte(nombre, nota):
    """Formatea un reporte con el nombre del estudiante y su nota."""
    # Se crea una cadena de texto que incluye el nombre y la nota
    reporte = f"Estudiante: {nombre} - Nota: {nota}"
    return reporte  # Se devuelve el reporte formateado

assert formatear_reporte("Ana", 18) == "Estudiante: Ana - Nota: 18"
