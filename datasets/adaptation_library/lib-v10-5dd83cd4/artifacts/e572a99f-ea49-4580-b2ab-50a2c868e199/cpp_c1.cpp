#include <iostream>
#include <vector>
#include <cassert>

std::vector<std::vector<int>> tabla_multiplicar(int n) {
    // Genera una tabla de multiplicar de tamaño n.
    std::vector<std::vector<int>> tabla;  // Inicializa la lista que contendrá las filas de la tabla
    for (int i = 1; i <= n; ++i) {  // Itera desde 1 hasta n
        std::vector<int> fila;  // Inicializa la fila actual
        for (int j = 1; j <= n; ++j) {  // Itera desde 1 hasta n para crear la fila
            fila.push_back(i * j);  // Agrega el producto a la fila
        }
        tabla.push_back(fila);  // Agrega la fila completa a la tabla
    }
    return tabla;  // Devuelve la tabla completa
}

int main() {
    // Verifica que la función devuelve la tabla de multiplicar correcta para n=2
    assert((tabla_multiplicar(2) == std::vector<std::vector<int>>{{1, 2}, {2, 4}}));
    std::cout << "OK" << std::endl;  // Imprime OK si todos los asserts pasan
    return 0;
}
