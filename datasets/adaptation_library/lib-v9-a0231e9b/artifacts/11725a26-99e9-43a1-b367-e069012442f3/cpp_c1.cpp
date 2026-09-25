#include <iostream>
#include <string>
#include <cassert>

// Función que clasifica la nota en categorías: excelente, regular o insuficiente.
std::string clasificar_nota(int nota) {
    // Verifica si la nota es mayor o igual a 16
    if (nota >= 16) {
        return "excelente";  // Retorna "excelente" si la nota es alta
    }
    // Verifica si la nota es mayor o igual a 10
    else if (nota >= 10) {
        return "regular";  // Retorna "regular" si la nota es aceptable
    } else {
        return "insuficiente";  // Retorna "insuficiente" si la nota es baja
    }
}

int main() {
    // Verifica que la clasificación de la nota 18 sea "excelente"
    assert(clasificar_nota(18) == "excelente");
    // Verifica que la clasificación de la nota 12 sea "regular"
    assert(clasificar_nota(12) == "regular");
    
    std::cout << "OK" << std::endl; // Imprime OK si todas las aserciones son correctas
    return 0;
}
