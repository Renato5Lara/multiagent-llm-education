#include <iostream>
#include <vector>
#include <cassert>

std::vector<int> contar_hasta(int n) {
    std::vector<int> resultado;
    int i = 1;
    while (i <= n) {
        resultado.push_back(i);
        i += 1;
    }
    return resultado;
}

int main() {
    assert((contar_hasta(3) == std::vector<int>{1, 2, 3}));
    std::cout << "OK" << std::endl;
    return 0;
}
