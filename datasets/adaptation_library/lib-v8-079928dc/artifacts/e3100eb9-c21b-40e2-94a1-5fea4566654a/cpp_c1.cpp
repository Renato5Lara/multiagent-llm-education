#include <iostream>
#include <cassert>

// Función que determina si un estudiante puede matricularse basado en requisitos y deudas.
bool puede_matricularse(bool tiene_requisitos, bool sin_deuda) {
    // Ambas condiciones deben ser verdaderas para que el estudiante pueda matricularse
    return tiene_requisitos && sin_deuda; // Retorna true solo si ambas condiciones son true
}

int main() {
    // Verifica que el estudiante puede matricularse si tiene requisitos y no tiene deudas
    assert(puede_matricularse(true, true) == true);
    // Verifica que el estudiante no puede matricularse si no tiene deudas pero no cumple los requisitos
    assert(puede_matricularse(true, false) == false);
    
    std::cout << "OK" << std::endl; // Imprime OK si todas las aserciones son verdaderas
    return 0;
}
