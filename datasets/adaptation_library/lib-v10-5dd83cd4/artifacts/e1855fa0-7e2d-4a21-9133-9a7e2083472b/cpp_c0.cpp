#include <iostream>
#include <vector>
#include <cassert>

int encontrar_mayor(const std::vector<int>& numeros) {
    int mayor = numeros[0];
    for (int num : numeros) {
        if (num > mayor) {
            mayor = num;
        }
    }
    return mayor;
}

int main() {
    assert(encontrar_mayor({3, 7, 2}) == 7);
    assert(encontrar_mayor({-1, -5, -2}) == -1);
    std::cout << "OK" << std::endl;
    return 0;
}
