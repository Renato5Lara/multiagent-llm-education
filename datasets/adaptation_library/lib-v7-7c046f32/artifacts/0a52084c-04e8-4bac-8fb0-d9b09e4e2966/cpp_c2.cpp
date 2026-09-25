#include <iostream>
#include <string>
#include <cassert>

std::string saludar(const std::string& nombre) {
    // Función que devuelve un saludo personalizado.
    // Verificamos si el nombre está vacío
    if (nombre.empty()) {
        return "Hola, invitado";  // Saludo por defecto si no se proporciona un nombre
    }
    // Retornamos el saludo personalizado
    return "Hola, " + nombre;
}

void ejemplo_uso() {
    // Función que ilustra el uso de la función saludar.
    std::cout << saludar("Ana") << std::endl;  // Debería imprimir: Hola, Ana
    std::cout << saludar("Luis") << std::endl;  // Debería imprimir: Hola, Luis
    std::cout << saludar("") << std::endl;      // Debería imprimir: Hola, invitado
}

int main() {
    // Asserts para verificar el comportamiento de la función saludar
    assert(saludar("Ana") == "Hola, Ana");
    assert(saludar("Luis") == "Hola, Luis");

    std::cout << "OK" << std::endl;
    return 0;
}
