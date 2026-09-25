#include <iostream>
#include <string>
#include <cassert>

std::string clasificar_estudiante(int nota, int asistencia) {
    /**
     * Clasifica el estado de un estudiante basado en su nota y asistencia.
     * 
     * Parámetros:
     * nota (int): La nota del estudiante.
     * asistencia (int): El porcentaje de asistencia del estudiante.
     * 
     * Retorna:
     * str: El estado del estudiante ("aprobado", "aprobado sin certificado" o "desaprobado").
     */
    
    // Verificar si la nota o la asistencia son valores extremos o inválidos
    if (nota < 0 || asistencia < 0) {
        return "entrada inválida";
    }
    
    // Clasificación del estudiante según la nota
    if (nota >= 10) {  // Si la nota es mayor o igual a 10
        if (asistencia >= 75) {  // Si la asistencia es mayor o igual a 75%
            return "aprobado";  // Estudiante aprobado
        } else {  // Si la asistencia es menor a 75%
            return "aprobado sin certificado";  // Estudiante aprobado sin certificado
        }
    } else {  // Si la nota es menor a 10
        return "desaprobado";  // Estudiante desaprobado
    }
}

void ejemplo_uso() {
    std::cout << clasificar_estudiante(15, 80) << std::endl;  // Debe imprimir "aprobado"
    std::cout << clasificar_estudiante(15, 50) << std::endl;  // Debe imprimir "aprobado sin certificado"
    std::cout << clasificar_estudiante(8, 90) << std::endl;   // Debe imprimir "desaprobado"
}

int main() {
    // Ejecutar asserts para verificar el comportamiento de la función
    assert(clasificar_estudiante(15, 80) == "aprobado");
    assert(clasificar_estudiante(15, 50) == "aprobado sin certificado");
    assert(clasificar_estudiante(8, 90) == "desaprobado");
    
    std::cout << "OK" << std::endl;
    return 0;
}
