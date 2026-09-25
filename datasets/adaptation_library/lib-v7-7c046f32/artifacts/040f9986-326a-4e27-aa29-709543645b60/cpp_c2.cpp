#include <iostream>
#include <vector>
#include <cassert>

int sumar_lista(const std::vector<int>& numeros) {
    /**
     * Suma los elementos de una lista de números.
     *
     * Parámetros:
     * numeros (std::vector<int>): Lista de números a sumar.
     *
     * Retorna:
     * int: La suma de los números en la lista. Si la lista está vacía, retorna 0.
     */
    int total = 0;  // Inicializa el total en 0
    for (int numero : numeros) {  // Itera sobre cada número en la lista
        total += numero;  // Suma el número actual al total
        std::cout << "total: " << total << std::endl;  // Traza el valor de total en cada vuelta
    }
    return total;  // Retorna la suma total
}

void ejemplo_uso() {
    /**
     * Ejemplo de uso de la función sumar_lista.
     */
    int resultado = sumar_lista({1, 2, 3});  // Llama a la función con una lista de ejemplo
    std::cout << "La suma de la lista es: " << resultado << std::endl;  // Imprime el resultado de la suma
}

int main() {
    // Estado inicial a nivel de módulo
    assert(sumar_lista({1, 2, 3}) == 6);
    std::cout << "OK" << std::endl;  // Imprime OK si los asserts pasan
    return 0;
}
