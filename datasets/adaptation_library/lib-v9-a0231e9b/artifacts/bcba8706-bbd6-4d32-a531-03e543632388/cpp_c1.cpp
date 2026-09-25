#include <iostream>
#include <string>
#include <cassert>

// Función que clasifica el estado del estudiante según su nota y asistencia.
std::string clasificar_estudiante(int nota, int asistencia) {
    // Verificamos si la nota es mayor o igual a 10
    if (nota >= 10) {
        // Si la asistencia es mayor o igual a 75, el estudiante está aprobado
        if (asistencia >= 75) {
            return "aprobado";
        } else {
            // Si la asistencia es menor a 75, el estudiante está aprobado sin certificado
            return "aprobado sin certificado";
        }
    } else {
        // Si la nota es menor a 10, el estudiante está desaprobado
        return "desaprobado";
    }
}

int main() {
    // Verificamos los resultados esperados con asserts
    assert(clasificar_estudiante(15, 80) == "aprobado");
    assert(clasificar_estudiante(15, 50) == "aprobado sin certificado");
    assert(clasificar_estudiante(8, 90) == "desaprobado");

    // Si todos los asserts pasan, imprimimos OK
    std::cout << "OK" << std::endl;
    return 0;
}
