#include <iostream>
#include <cassert>

// Función que calcula el área de un rectángulo dado su base y altura.
int calcular_area_rectangulo(int base, int altura) {
    // Multiplica la base por la altura para obtener el área
    int area = base * altura;
    return area;
}

int main() {
    // Calcula el área con base 6 y altura 3.
    int area_rectangulo = calcular_area_rectangulo(6, 3);
    
    // Verifica que el área de un rectángulo con base 4 y altura 5 sea 20.
    assert(calcular_area_rectangulo(4, 5) == 20);
    
    // Imprime OK si todas las aserciones son correctas.
    std::cout << "OK" << std::endl;
    return 0;
}
