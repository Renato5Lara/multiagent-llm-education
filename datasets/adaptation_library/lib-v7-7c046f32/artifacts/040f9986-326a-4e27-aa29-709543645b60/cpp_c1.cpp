#include <iostream>
#include <vector>
#include <cassert>

int sumar_lista(const std::vector<int>& numeros) {
    // Suma los elementos de una lista.
    int total = 0;  // Inicializa el total en 0
    for (int numero : numeros) {  // Itera sobre cada número en la lista
        total += numero;  // Suma el número actual al total
        // Traza el valor de total en cada vuelta
        std::cout << "total: " << total << std::endl; // Imprime el total en cada iteración
    }
    return total;  // Devuelve el total final
}

int main() {
    // Verifica el resultado en un entorno de prueba.
    assert(sumar_lista({1, 2, 3}) == 6);
    std::cout << "OK" << std::endl; // Imprime OK si la aserción es correcta
    return 0;
}
