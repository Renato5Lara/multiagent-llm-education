#include <iostream>
#include <string>
#include <cassert>

float convertir_a_numero(const std::string& texto) {
    return texto.find('.') != std::string::npos ? std::stof(texto) : std::stoi(texto);
}

int main() {
    assert(convertir_a_numero("10") == 10);
    assert(convertir_a_numero("3.5") == 3.5);
    std::cout << "OK" << std::endl;
    return 0;
}
