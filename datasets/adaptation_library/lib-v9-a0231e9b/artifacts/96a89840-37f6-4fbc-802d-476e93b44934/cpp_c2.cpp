#include <iostream>
#include <vector>
#include <cassert>

std::vector<int> obtener_primeros_tres(const std::vector<int>& lista) {
    /**
     * Obtiene los primeros tres elementos de una lista.
     *
     * Parámetros:
     * lista (std::vector<int>): La lista de la cual se extraerán los primeros tres elementos.
     *
     * Retorna:
     * std::vector<int>: Una lista con los primeros tres elementos. Si la lista tiene menos de tres elementos,
     * se devolverá la lista completa.
     */
    // Verificamos si la lista está vacía
    if (lista.empty()) {
        return {};
    }
    
    // Devolvemos los primeros tres elementos usando slicing
    return std::vector<int>(lista.begin(), lista.begin() + std::min(3, static_cast<int>(lista.size())));
}

void ejemplo_uso() {
    // Ejemplo de uso de la función obtener_primeros_tres
    std::cout << "Ejemplo de uso de obtener_primeros_tres:" << std::endl;
    for (const auto& elem : obtener_primeros_tres({1, 2, 3, 4, 5})) {
        std::cout << elem << " ";  // Debería imprimir 1 2 3
    }
    std::cout << std::endl;

    for (const auto& elem : obtener_primeros_tres({10, 20})) {
        std::cout << elem << " ";  // Debería imprimir 10 20
    }
    std::cout << std::endl;

    for (const auto& elem : obtener_primeros_tres({})) {
        std::cout << elem << " ";  // Debería imprimir nada
    }
    std::cout << std::endl;

    for (const auto& elem : obtener_primeros_tres({100})) {
        std::cout << elem << " ";  // Debería imprimir 100
    }
    std::cout << std::endl;

    for (const auto& elem : obtener_primeros_tres({1, 2, 3, 4, 5, 6})) {
        std::cout << elem << " ";  // Debería imprimir 1 2 3
    }
    std::cout << std::endl;
}

int main() {
    // Ejecutamos los asserts para verificar el comportamiento de la función
    assert(obtener_primeros_tres({1, 2, 3, 4, 5}) == std::vector<int>({1, 2, 3}));
    
    // Llamamos a ejemplo_uso para mostrar el uso de la función
    ejemplo_uso();

    std::cout << "OK" << std::endl;
    return 0;
}
