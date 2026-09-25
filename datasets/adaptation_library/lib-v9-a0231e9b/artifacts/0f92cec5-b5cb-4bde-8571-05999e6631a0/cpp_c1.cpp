#include <iostream>
#include <vector>
#include <cassert> // Para las aserciones

// Función que devuelve el primer y último elemento de la lista
std::pair<int, int> obtener_primero_y_ultimo(const std::vector<int>& lista) {
    // El primer elemento se obtiene con el índice 0
    int primero = lista[0];
    // El último elemento se obtiene con el índice -1, que en C++ se traduce como lista[lista.size() - 1]
    int ultimo = lista[lista.size() - 1];
    // Retorna un par con el primer y último elemento
    return std::make_pair(primero, ultimo);
}

int main() {
    // Aserción para verificar que la función devuelve los valores esperados
    assert(obtener_primero_y_ultimo({10, 20, 30}) == std::make_pair(10, 30));
    std::cout << "OK" << std::endl; // Imprime OK si la aserción es correcta
    return 0; // Fin del programa
}
