def calcular_iva(precio):
    """Calcula el IVA del precio dado.
    
    Args:
        precio (float): El precio sobre el cual se calculará el IVA.
        
    Returns:
        float: El monto del IVA calculado.
        
    Raises:
        ValueError: Si el precio es negativo.
    """
    # Verificar si el precio es negativo
    if precio < 0:
        raise ValueError("El precio no puede ser negativo.")
    
    # Definir la tasa de IVA
    tasa_iva = 0.18
    
    # Calcular el IVA
    iva = precio * tasa_iva
    
    return iva

def ejemplo_uso():
    """Ejemplo de uso de la función calcular_iva."""
    # Ejemplo con un precio de 100
    precio = 100
    print(f"El IVA de {precio} es: {calcular_iva(precio)}")
    
total = calcular_iva(100)
