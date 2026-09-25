def calcular_iva(precio):
    """
    Calcula el IVA (Impuesto al Valor Agregado) de un precio dado.
    
    Parámetros:
    precio (float): El precio sobre el cual se calculará el IVA.
    
    Retorna:
    float: El monto del IVA calculado. Si el precio es menor o igual a cero, retorna 0.0.
    """
    # Verificamos si el precio es menor o igual a cero
    if precio <= 0:
        return 0.0  # Retornamos 0.0 para precios no válidos
    
    # Definimos la tasa de IVA
    tasa_iva = 0.18  # 18% de IVA
    
    # Calculamos el IVA
    iva = precio * tasa_iva
    
    return iva  # Retornamos el monto del IVA calculado

def ejemplo_uso():
    # Ejemplo de uso de la función calcular_iva
    print("IVA de 100:", calcular_iva(100))  # Debería imprimir 18.0
    print("IVA de 0:", calcular_iva(0))      # Debería imprimir 0.0
    print("IVA de -50:", calcular_iva(-50))  # Debería imprimir 0.0
    print("IVA de 200:", calcular_iva(200))  # Debería imprimir 36.0

assert calcular_iva(100) == 18.0
