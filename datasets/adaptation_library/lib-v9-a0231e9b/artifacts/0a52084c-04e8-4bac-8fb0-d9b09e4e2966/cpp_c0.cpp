#include <iostream>
#include <string>
#include <cassert>

std::string saludar(const std::string& nombre) {
    return "Hola, " + nombre;
}

int main() {
    assert(saludar("Ana") == "Hola, Ana");
    assert(saludar("Luis") == "Hola, Luis");
    std::cout << "OK" << std::endl;
    return 0;
}
