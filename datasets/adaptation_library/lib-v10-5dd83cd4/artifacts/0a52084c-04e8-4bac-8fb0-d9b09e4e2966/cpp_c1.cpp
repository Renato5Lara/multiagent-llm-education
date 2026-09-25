#include <iostream>
#include <string>
#include <cassert>

// Definición de la función saludar que toma un nombre como argumento
std::string saludar(const std::string& nombre) {
    // Devuelve un saludo personalizado.
    // Se crea el saludo concatenando "Hola, " con el nombre proporcionado
    std::string saludo = "Hola, " + nombre;
    return saludo;  // Se retorna el saludo generado
}

int main() {
    // Se ejecutan los asserts para verificar que la función saludar funciona correctamente
    assert(saludar("Ana") == "Hola, Ana");
    assert(saludar("Luis") == "Hola, Luis");

    // Si todos los asserts pasan, se imprime OK
    std::cout << "OK" << std::endl;
    return 0;
}
