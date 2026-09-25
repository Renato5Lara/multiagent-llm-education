#include <iostream>
#include <vector>
#include <cassert>

int sumar_lista(const std::vector<int>& numeros) {
    int suma = 0;
    for (int numero : numeros) {
        suma += numero;
    }
    return suma;
}

int main() {
    assert(sumar_lista({1, 2, 3}) == 6);
    std::cout << "OK" << std::endl;
    return 0;
}
