#include <iostream>
#include <vector>
#include <algorithm>
#include <cassert>

std::vector<int> actualizar_lista(std::vector<int> lista) {
    lista.push_back(40);
    lista.insert(lista.begin(), 5);
    lista.erase(std::remove(lista.begin(), lista.end(), 20), lista.end());
    lista.pop_back();
    return lista;
}

int main() {
    assert((actualizar_lista(std::vector<int>{10, 20, 30}) == std::vector<int>{5, 10, 30}));
    std::cout << "OK" << std::endl;
    return 0;
}
