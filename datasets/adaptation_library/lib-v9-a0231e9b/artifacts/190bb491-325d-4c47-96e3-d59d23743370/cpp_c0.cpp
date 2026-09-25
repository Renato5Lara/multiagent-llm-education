#include <iostream>
#include <vector>
#include <cassert>

std::vector<int> crear_lista_de_notas() {
    return {12, 15, 18, 9};
}

int main() {
    assert((crear_lista_de_notas() == std::vector<int>{12, 15, 18, 9}));
    std::cout << "OK" << std::endl;
    return 0;
}
