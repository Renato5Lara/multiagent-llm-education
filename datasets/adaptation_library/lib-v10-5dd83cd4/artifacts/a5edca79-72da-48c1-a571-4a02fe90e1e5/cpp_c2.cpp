#include <iostream>
#include <string>
#include <cassert>

std::string formatear_reporte(const std::string& nombre, int nota) {
    /*
    Formatea un reporte con el nombre del estudiante y su nota.
    
    Parámetros:
    nombre (std::string): El nombre del estudiante.
    nota (int): La nota del estudiante.
    
    Retorna:
    std::string: Un string formateado con el nombre y la nota del estudiante.
    */
    
    // Verificar si el nombre está vacío
    std::string nombre_final = nombre.empty() ? "Nombre no proporcionado" : nombre;
    
    // Verificar si la nota es un número válido
    if (nota < 0) {
        nota = 0;
    } else if (nota > 20) {
        nota = 20;
    }
    
    // Formatear el reporte
    return "Estudiante: " + nombre_final + " - Nota: " + std::to_string(nota);
}

void ejemplo_uso() {
    // Ejemplo de uso de la función formatear_reporte
    std::cout << formatear_reporte("Ana", 18) << std::endl;  // Salida esperada: "Estudiante: Ana - Nota: 18"
    std::cout << formatear_reporte("", 15) << std::endl;      // Salida esperada: "Estudiante: Nombre no proporcionado - Nota: 15"
    std::cout << formatear_reporte("Luis", -5) << std::endl;  // Salida esperada: "Estudiante: Luis - Nota: 0"
    std::cout << formatear_reporte("Marta", 25) << std::endl; // Salida esperada: "Estudiante: Marta - Nota: 20"
}

int main() {
    // Ejecutar asserts para verificar el comportamiento de la función
    assert(formatear_reporte("Ana", 18) == "Estudiante: Ana - Nota: 18");
    
    // Imprimir OK si todos los asserts pasan
    std::cout << "OK" << std::endl;
    
    return 0;
}
