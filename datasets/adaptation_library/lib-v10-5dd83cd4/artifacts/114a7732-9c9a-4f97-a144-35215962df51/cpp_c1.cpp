#include <iostream>
#include <cassert>

// Función que determina si la nota es suficiente para aprobar.
bool aprobo(int nota) {
    // Compara la nota con el valor mínimo de aprobación
    return nota >= 11; // Retorna true si la nota es mayor o igual a 11, de lo contrario false
}

int main() {
    // Verifica que la función aprobo funcione correctamente
    assert(aprobo(11) == true);  // Asegura que 11 es aprobado
    assert(aprobo(10) == false); // Asegura que 10 no es aprobado

    std::cout << "OK" << std::endl; // Imprime OK si todas las aserciones son verdaderas
    return 0; // Finaliza el programa
}
