#include <iostream>
#include <cassert>

bool puede_matricularse(bool tiene_requisitos, bool sin_deuda) {
    /**
     * Determina si un estudiante puede matricularse en función de dos condiciones:
     * 1. Si tiene los requisitos necesarios.
     * 2. Si no tiene deudas pendientes.
     *
     * Ambas condiciones deben ser verdaderas para que el estudiante pueda matricularse.
     *
     * @param tiene_requisitos: bool, indica si el estudiante tiene los requisitos.
     * @param sin_deuda: bool, indica si el estudiante no tiene deudas.
     * @return: bool, True si puede matricularse, False en caso contrario.
     */
    // Se evalúan ambas condiciones usando el operador lógico and
    return tiene_requisitos && sin_deuda;
}

void ejemplo_uso() {
    // Ejemplo de uso de la función puede_matricularse
    std::cout << std::boolalpha; // Para imprimir bool como true/false
    std::cout << puede_matricularse(true, true) << std::endl;   // Debería imprimir true
    std::cout << puede_matricularse(true, false) << std::endl;  // Debería imprimir false
    std::cout << puede_matricularse(false, true) << std::endl;  // Debería imprimir false
    std::cout << puede_matricularse(false, false) << std::endl; // Debería imprimir false
}

int main() {
    // Ejecutar asserts para verificar el comportamiento de la función
    assert(puede_matricularse(true, true) == true);
    assert(puede_matricularse(true, false) == false);
    
    std::cout << "OK" << std::endl; // Imprimir OK si todos los asserts pasan
    return 0;
}
