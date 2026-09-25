#include <iostream>
#include <vector>
#include <cassert>

// Función que devuelve los primeros tres elementos de la lista
std::vector<int> obtener_primeros_tres(const std::vector<int>& lista) {
    // Se utiliza slicing para obtener los primeros tres elementos
    return std::vector<int>(lista.begin(), lista.begin() + std::min(3, static_cast<int>(lista.size()))); // Retorna los elementos desde el inicio hasta el índice 3 (sin incluirlo)
}

int main() {
    // Afirmación para verificar que la función devuelve los primeros tres elementos correctamente
    assert(obtener_primeros_tres({1, 2, 3, 4, 5}) == std::vector<int>({1, 2, 3}));
    
    // Si todas las afirmaciones son correctas, imprime OK
    std::cout << "OK" << std::endl;
    return 0;
}
