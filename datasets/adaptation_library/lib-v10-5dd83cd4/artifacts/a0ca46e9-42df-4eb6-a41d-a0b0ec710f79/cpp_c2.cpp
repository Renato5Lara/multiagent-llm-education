#include <iostream>
#include <vector>
#include <algorithm>
#include <cassert>

std::vector<int> actualizar_lista(std::vector<int> lista) {
    // Verificamos si la lista está vacía
    if (lista.empty()) {
        return lista;  // Retornamos la lista vacía si no hay elementos
    }

    // Operación append: añadimos 40 al final de la lista
    lista.push_back(40);
    // Traza después de append
    std::cout << "[";
    for (size_t i = 0; i < lista.size(); ++i) {
        std::cout << lista[i] << (i < lista.size() - 1 ? ", " : "");
    }
    std::cout << "]" << std::endl;  // [10, 20, 30, 40]

    // Operación insert: añadimos 5 en la posición 0
    lista.insert(lista.begin(), 5);
    // Traza después de insert
    std::cout << "[";
    for (size_t i = 0; i < lista.size(); ++i) {
        std::cout << lista[i] << (i < lista.size() - 1 ? ", " : "");
    }
    std::cout << "]" << std::endl;  // [5, 10, 20, 30, 40]

    // Operación remove: eliminamos el valor 20
    lista.erase(std::remove(lista.begin(), lista.end(), 20), lista.end());
    // Traza después de remove
    std::cout << "[";
    for (size_t i = 0; i < lista.size(); ++i) {
        std::cout << lista[i] << (i < lista.size() - 1 ? ", " : "");
    }
    std::cout << "]" << std::endl;  // [5, 10, 30, 40]

    // Operación pop: eliminamos el último elemento
    lista.pop_back();
    // Traza después de pop
    std::cout << "[";
    for (size_t i = 0; i < lista.size(); ++i) {
        std::cout << lista[i] << (i < lista.size() - 1 ? ", " : "");
    }
    std::cout << "]" << std::endl;  // [5, 10, 30]

    return lista;  // Retornamos la lista final
}

void ejemplo_uso() {
    std::vector<int> resultado = actualizar_lista({10, 20, 30});
    std::cout << "Resultado final: [";
    for (size_t i = 0; i < resultado.size(); ++i) {
        std::cout << resultado[i] << (i < resultado.size() - 1 ? ", " : "");
    }
    std::cout << "]" << std::endl;  // Debería mostrar: Resultado final: [5, 10, 30]
}

int main() {
    assert((actualizar_lista({10, 20, 30}) == std::vector<int>{5, 10, 30}));
    std::cout << "OK" << std::endl;
    return 0;
}
