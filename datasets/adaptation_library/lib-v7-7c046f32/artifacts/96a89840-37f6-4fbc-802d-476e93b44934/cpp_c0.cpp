#include <iostream>
#include <vector>
#include <cassert>

std::vector<int> obtener_primeros_tres(const std::vector<int>& lista) {
    return std::vector<int>(lista.begin(), lista.begin() + std::min(static_cast<size_t>(3), lista.size()));
}

int main() {
    assert(obtener_primeros_tres({1, 2, 3, 4, 5}) == std::vector<int>({1, 2, 3}));
    std::cout << "OK" << std::endl;
    return 0;
}
