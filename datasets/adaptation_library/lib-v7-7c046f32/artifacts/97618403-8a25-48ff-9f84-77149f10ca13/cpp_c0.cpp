#include <iostream>
#include <string>
#include <cassert>

std::string crear_saludo(const std::string& nombre, const std::string& saludo = "Hola") {
    return saludo + ", " + nombre;
}

int main() {
    assert(crear_saludo("Ana") == "Hola, Ana");
    assert(crear_saludo("Ana", "Buenas") == "Buenas, Ana");
    std::cout << "OK" << std::endl;
    return 0;
}
