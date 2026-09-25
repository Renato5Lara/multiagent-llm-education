#include <iostream>
#include <string>
#include <cassert>

int leer_edad(const std::string& texto_ingresado) {
    return std::stoi(texto_ingresado);
}

int main() {
    assert(leer_edad("18") == 18);
    assert(leer_edad("25") == 25);
    std::cout << "OK" << std::endl;
    return 0;
}
