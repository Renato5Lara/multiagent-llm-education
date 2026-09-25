#include <iostream>
#include <cassert>

int calcular_area_rectangulo(int base, int altura) {
    return base * altura;
}

int main() {
    assert(calcular_area_rectangulo(4, 5) == 20);
    std::cout << "OK" << std::endl;
    return 0;
}
