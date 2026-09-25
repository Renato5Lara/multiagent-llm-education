def encontrar_mayor(numeros):
    """Encuentra el mayor número en una lista de números."""
    # Tomar el primer número como candidato inicial
    mayor = numeros[0]
    
    # Recorrer la lista de números
    for numero in numeros:
        # Comparar el número actual con el candidato
        if numero > mayor:
            # Actualizar el candidato si se encuentra un número mayor
            mayor = numero
            
    # Devolver el mayor número encontrado
    return mayor
