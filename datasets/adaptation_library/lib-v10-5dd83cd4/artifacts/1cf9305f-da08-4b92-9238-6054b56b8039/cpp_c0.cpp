#include <iostream>
#include <vector>
#include <numeric>
#include <cassert>

double procesar_promedio(const std::vector<int>& notas) {
    return static_cast<double>(std::accumulate(notas.begin(), notas.end(), 0)) / notas.size();
}

int main() {
    assert(procesar_promedio({10, 20, 30}) == 20);
    std::cout << "OK" << std::endl;
    return 0;
}
