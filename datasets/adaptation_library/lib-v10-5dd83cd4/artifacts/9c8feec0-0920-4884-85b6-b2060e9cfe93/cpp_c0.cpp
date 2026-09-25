#include <iostream>
#include <cassert>

double calcular_iva(double precio) {
    return precio * 0.18;
}

int main() {
    assert((calcular_iva(100) == 18.0));
    std::cout << "OK" << std::endl;
    return 0;
}
