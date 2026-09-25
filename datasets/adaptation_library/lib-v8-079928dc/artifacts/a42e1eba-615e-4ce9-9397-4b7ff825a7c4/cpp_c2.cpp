#include <iostream>
#include <cassert>

float calcular_area_rectangulo(float base, float altura) {
    /**
     * Calcula el área de un rectángulo dado su base y altura.
     *
     * Parámetros:
     * base (float): La base del rectángulo.
     * altura (float): La altura del rectángulo.
     *
     * Retorna:
     * float: El área del rectángulo calculada como base * altura.
     */
    // Verificar si la base o la altura son cero o negativos
    if (base <= 0 || altura <= 0) {
        return 0;  // El área no puede ser negativa o cero
    }

    // Calcular el área multiplicando base por altura
    float area = base * altura;
    return area;
}

void ejemplo_uso() {
    // Ejemplo de uso de la función calcular_area_rectangulo
    std::cout << calcular_area_rectangulo(6, 3) << std::endl;  // Debería imprimir 18
    std::cout << calcular_area_rectangulo(4, 5) << std::endl;  // Debería imprimir 20
    std::cout << calcular_area_rectangulo(0, 5) << std::endl;  // Debería imprimir 0
    std::cout << calcular_area_rectangulo(4, -2) << std::endl; // Debería imprimir 0
    std::cout << calcular_area_rectangulo(10, 10) << std::endl; // Debería imprimir 100
}

int main() {
    // Ejecutar asserts para verificar el comportamiento de la función
    assert(calcular_area_rectangulo(4, 5) == 20);
    
    // Imprimir OK si todos los asserts pasan
    std::cout << "OK" << std::endl;

    return 0;
}
