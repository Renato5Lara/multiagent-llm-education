#include <iostream>
#include <cassert>

int suma_hasta(int n) {
    return n * (n + 1) / 2;
}

int main() {
    assert(suma_hasta(5) == 15);
    assert(suma_hasta(1) == 1);
    std::cout << "OK" << std::endl;
    return 0;
}
