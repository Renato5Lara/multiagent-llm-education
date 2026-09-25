#include <iostream>
#include <vector>
#include <string>
#include <cassert>

int buscar_estudiante(const std::vector<std::string>& lista, const std::string& nombre) {
    /**
     * Busca el nombre de un estudiante en una lista y devuelve su índice.
     * 
     * Parámetros:
     * lista (std::vector<std::string>): Lista de nombres de estudiantes.
     * nombre (std::string): Nombre del estudiante a buscar.
     * 
     * Retorna:
     * int: El índice del estudiante en la lista si se encuentra, 
     *      o -1 si no se encuentra.
     */
    
    // Verificamos si la lista está vacía
    if (lista.empty()) {
        return -1;  // Retornamos -1 si la lista está vacía
    }
    
    // Verificamos si el nombre está en la lista
    for (size_t i = 0; i < lista.size(); ++i) {
        if (lista[i] == nombre) {
            // Si el nombre está, retornamos su índice
            return static_cast<int>(i);
        }
    }
    
    // Si el nombre no está, retornamos -1
    return -1;
}

void ejemplo_uso() {
    // Ejemplo de uso de la función buscar_estudiante
    std::vector<std::string> estudiantes = {"Ana", "Luis", "Pedro"};
    std::cout << buscar_estudiante(estudiantes, "Luis") << std::endl;  // Debería imprimir 1
    std::cout << buscar_estudiante(estudiantes, "Marco") << std::endl;  // Debería imprimir -1
    std::cout << buscar_estudiante({}, "Ana") << std::endl;  // Debería imprimir -1
    std::cout << buscar_estudiante({"Juan"}, "Juan") << std::endl;  // Debería imprimir 0
    std::cout << buscar_estudiante({"Juan"}, "Pedro") << std::endl;  // Debería imprimir -1
}

int main() {
    // Asserts para verificar el comportamiento de la función
    assert(buscar_estudiante({"Ana", "Luis"}, "Luis") == 1);
    assert(buscar_estudiante({"Ana", "Luis"}, "Marco") == -1);
    
    std::cout << "OK" << std::endl;
    return 0;
}
