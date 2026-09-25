#include <iostream>
#include <vector>
#include <string>
#include <cassert>

// Función que busca el nombre de un estudiante en la lista y devuelve su índice o -1 si no está.
int buscar_estudiante(const std::vector<std::string>& lista, const std::string& nombre) {
    // Verifica si el nombre está en la lista
    for (size_t i = 0; i < lista.size(); ++i) {
        if (lista[i] == nombre) {
            return static_cast<int>(i); // Devuelve el índice del nombre
        }
    }
    return -1; // Devuelve -1 si el nombre no está en la lista
}

int main() {
    // Verifica que la función devuelve el índice correcto para "Luis"
    assert(buscar_estudiante({"Ana", "Luis"}, "Luis") == 1);
    // Verifica que la función devuelve -1 para un nombre que no está en la lista
    assert(buscar_estudiante({"Ana", "Luis"}, "Marco") == -1);
    
    std::cout << "OK" << std::endl; // Imprime OK si todas las aserciones son correctas
    return 0;
}
