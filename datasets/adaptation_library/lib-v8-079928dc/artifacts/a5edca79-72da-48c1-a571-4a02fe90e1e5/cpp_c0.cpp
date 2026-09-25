#include <iostream>
#include <string>
#include <cassert>

std::string formatear_reporte(const std::string& nombre, int nota) {
    return "Estudiante: " + nombre + " - Nota: " + std::to_string(nota);
}

int main() {
    assert(formatear_reporte("Ana", 18) == "Estudiante: Ana - Nota: 18");
    std::cout << "OK" << std::endl;
    return 0;
}
