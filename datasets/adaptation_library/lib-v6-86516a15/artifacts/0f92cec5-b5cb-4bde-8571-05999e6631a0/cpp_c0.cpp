#include <iostream>
#include <vector>
#include <cassert>

std::pair<int, int> obtener_primero_y_ultimo(const std::vector<int>& lista) {
    return {lista[0], lista[lista.size() - 1]};
}

int main() {
    assert(obtener_primero_y_ultimo({10, 20, 30}) == std::make_pair(10, 30));
    std::cout << "OK" << std::endl;
    return 0;
}
