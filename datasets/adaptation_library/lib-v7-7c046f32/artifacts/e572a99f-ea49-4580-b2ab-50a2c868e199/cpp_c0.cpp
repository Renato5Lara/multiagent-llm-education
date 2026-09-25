#include <iostream>
#include <vector>
#include <cassert>

std::vector<std::vector<int>> tabla_multiplicar(int n) {
    std::vector<std::vector<int>> resultado;
    for (int i = 1; i <= n; ++i) {
        resultado.push_back({i, i * n});
    }
    return resultado;
}

int main() {
    assert((tabla_multiplicar(2) == std::vector<std::vector<int>>{{1, 2}, {2, 4}}));
    std::cout << "OK" << std::endl;
    return 0;
}
