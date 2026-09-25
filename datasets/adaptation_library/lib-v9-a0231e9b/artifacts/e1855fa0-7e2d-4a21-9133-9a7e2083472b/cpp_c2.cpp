#include <iostream>
#include <vector>
#include <cassert>
#include <limits>

int encontrar_mayor(const std::vector<int>& numeros) {
    /*
    Encuentra el número mayor en una lista de números.

    Parámetros:
    numeros (vector<int>): Lista de números enteros.

    Retorna:
    int: El número mayor de la lista. Si la lista está vacía, retorna std::numeric_limits<int>::min().
    */
    // Manejo de caso límite: si la lista está vacía, retornar un valor mínimo
    if (numeros.empty()) {
        return std::numeric_limits<int>::min();
    }
    
    // Tomar un candidato inicial, el primer elemento de la lista
    int mayor = numeros[0];
    
    // Comparar cada número en la lista con el candidato actual
    for (const int& numero : numeros) {
        // Si encontramos un número mayor, actualizar el candidato
        if (numero > mayor) {
            mayor = numero;
        }
    }
    
    // Retornar el mayor encontrado
    return mayor;
}

void ejemplo_uso() {
    std::cout << encontrar_mayor({3, 7, 2}) << std::endl;  // Debería imprimir 7
    std::cout << encontrar_mayor({-1, -5, -2}) << std::endl;  // Debería imprimir -1
    std::cout << encontrar_mayor({}) << std::endl;  // Debería imprimir un valor mínimo
    std::cout << encontrar_mayor({0, 0, 0}) << std::endl;  // Debería imprimir 0
    std::cout << encontrar_mayor({100, 200, 300}) << std::endl;  // Debería imprimir 300
}

int main() {
    // Ejecutar asserts para verificar el funcionamiento de la función
    assert(encontrar_mayor({3, 7, 2}) == 7);
    assert(encontrar_mayor({-1, -5, -2}) == -1);
    
    std::cout << "OK" << std::endl;
    return 0;
}
