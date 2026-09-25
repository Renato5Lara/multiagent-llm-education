#include <iostream>
#include <cassert>

double calcular_promedio_ponderado(double n1, double n2, double n3) {
    return (n1 + n2 + n3) / 3;
}

int main() {
    assert(calcular_promedio_ponderado(10, 10, 10) == 10);
    std::cout << "OK" << std::endl;
    return 0;
}
