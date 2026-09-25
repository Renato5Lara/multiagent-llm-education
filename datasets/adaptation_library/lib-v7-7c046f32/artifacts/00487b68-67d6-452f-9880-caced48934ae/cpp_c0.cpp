#include <iostream>
#include <cassert>

bool es_par(int numero) {
    return numero % 2 == 0;
}

int repartir_exacto(int total, int personas) {
    return total / personas;
}

int main() {
    assert(es_par(4) == true);
    assert(es_par(7) == false);
    assert(repartir_exacto(10, 3) == 3);
    std::cout << "OK" << std::endl;
    return 0;
}
