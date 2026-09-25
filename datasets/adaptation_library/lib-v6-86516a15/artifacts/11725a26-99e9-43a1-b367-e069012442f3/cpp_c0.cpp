#include <iostream>
#include <cassert>
#include <string>

std::string clasificar_nota(int nota) {
    if (nota >= 16) {
        return "excelente";
    } else if (nota >= 10) {
        return "regular";
    } else {
        return "deficiente";
    }
}

int main() {
    assert(clasificar_nota(18) == "excelente");
    assert(clasificar_nota(12) == "regular");
    std::cout << "OK" << std::endl;
    return 0;
}
