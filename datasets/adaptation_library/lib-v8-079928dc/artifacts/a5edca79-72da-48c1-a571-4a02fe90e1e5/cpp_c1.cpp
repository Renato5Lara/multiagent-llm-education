#include <iostream>
#include <string>
#include <cassert>

// Función que formatea y devuelve un reporte del estudiante con su nombre y nota.
std::string formatear_reporte(const std::string& nombre, int nota) {
    // Se crea un string formateado con el nombre y la nota del estudiante
    return "Estudiante: " + nombre + " - Nota: " + std::to_string(nota);
}

int main() {
    // Se verifica que la función formatear_reporte funcione correctamente
    assert(formatear_reporte("Ana", 18) == "Estudiante: Ana - Nota: 18");
    
    // Si todos los asserts pasan, se imprime OK
    std::cout << "OK" << std::endl;
    return 0;
}
