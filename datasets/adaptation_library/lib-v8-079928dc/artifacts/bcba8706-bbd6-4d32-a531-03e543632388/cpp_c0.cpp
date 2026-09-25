#include <iostream>
#include <string>
#include <cassert>

std::string clasificar_estudiante(int nota, int asistencia) {
    if (nota >= 10) {
        if (asistencia >= 75) {
            return "aprobado";
        } else {
            return "aprobado sin certificado";
        }
    } else {
        return "desaprobado";
    }
}

int main() {
    assert(clasificar_estudiante(15, 80) == "aprobado");
    assert(clasificar_estudiante(15, 50) == "aprobado sin certificado");
    assert(clasificar_estudiante(8, 90) == "desaprobado");
    std::cout << "OK" << std::endl;
    return 0;
}
