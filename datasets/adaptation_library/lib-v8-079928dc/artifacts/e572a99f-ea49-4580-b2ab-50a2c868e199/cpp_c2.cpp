#include <iostream>
#include <vector>
#include <cassert>

std::vector<std::vector<int>> tabla_multiplicar(int n) {
    /**
     * Genera una tabla de multiplicar de tamaño n x n.
     * 
     * Parámetros:
     * n (int): El tamaño de la tabla de multiplicar.
     * 
     * Retorna:
     * std::vector<std::vector<int>>: Una lista de listas que representa la tabla de multiplicar.
     */
    // Manejo de casos límite
    if (n <= 0) {  // Si n es cero o negativo, retornamos una lista vacía
        return {};
    }
    
    // Inicializamos la tabla
    std::vector<std::vector<int>> tabla;
    
    // Creamos la tabla de multiplicar
    for (int i = 1; i <= n; ++i) {  // Iteramos desde 1 hasta n
        std::vector<int> fila;  // Inicializamos una nueva fila
        for (int j = 1; j <= n; ++j) {  // Iteramos desde 1 hasta n para las columnas
            fila.push_back(i * j);  // Agregamos el producto a la fila
        }
        tabla.push_back(fila);  // Agregamos la fila a la tabla
    }
    
    return tabla;  // Retornamos la tabla completa
}

void ejemplo_uso() {
    /**
     * Función que ilustra el uso de la función tabla_multiplicar.
     */
    std::cout << "Tabla de multiplicar de 2:\n";
    for (const auto& fila : tabla_multiplicar(2)) {
        for (const auto& valor : fila) {
            std::cout << valor << " ";
        }
        std::cout << "\n";
    }
    
    std::cout << "Tabla de multiplicar de 3:\n";
    for (const auto& fila : tabla_multiplicar(3)) {
        for (const auto& valor : fila) {
            std::cout << valor << " ";
        }
        std::cout << "\n";
    }
    
    std::cout << "Tabla de multiplicar de 0:\n";
    for (const auto& fila : tabla_multiplicar(0)) {
        for (const auto& valor : fila) {
            std::cout << valor << " ";
        }
        std::cout << "\n";
    }
    
    std::cout << "Tabla de multiplicar de -1:\n";
    for (const auto& fila : tabla_multiplicar(-1)) {
        for (const auto& valor : fila) {
            std::cout << valor << " ";
        }
        std::cout << "\n";
    }
}

int main() {
    // Asserts para verificar el comportamiento de la función
    assert((tabla_multiplicar(2) == std::vector<std::vector<int>>{{1, 2}, {2, 4}}));
    assert((tabla_multiplicar(3) == std::vector<std::vector<int>>{{1, 2, 3}, {2, 4, 6}, {3, 6, 9}}));
    assert((tabla_multiplicar(0) == std::vector<std::vector<int>>{}));
    assert((tabla_multiplicar(-1) == std::vector<std::vector<int>>{}));
    
    std::cout << "OK\n";
    return 0;
}
