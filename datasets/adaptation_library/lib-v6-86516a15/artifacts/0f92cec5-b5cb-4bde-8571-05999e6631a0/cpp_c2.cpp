#include <iostream>
#include <vector>
#include <tuple>
#include <cassert>

std::tuple<int, int> obtener_primero_y_ultimo(const std::vector<int>& lista) {
    /**
     * Obtiene el primer y el último elemento de una lista.
     * 
     * Parámetros:
     * lista (vector<int>): La lista de la cual se extraerán los elementos.
     * 
     * Retorna:
     * tuple: Una tupla con el primer y el último elemento de la lista.
     *        Si la lista está vacía, retorna (0, 0).
     */
    // Verificamos si la lista está vacía
    if (lista.empty()) {
        return std::make_tuple(0, 0);  // Retornamos 0 para ambos elementos si la lista está vacía
    }
    
    // Obtenemos el primer elemento
    int primero = lista[0];  // El primer elemento se encuentra en el índice 0
    
    // Obtenemos el último elemento usando indexación negativa
    int ultimo = lista[lista.size() - 1];  // El último elemento se encuentra en el índice -1
    
    // Retornamos una tupla con el primer y el último elemento
    return std::make_tuple(primero, ultimo);
}

void ejemplo_uso() {
    // Ejemplo de uso de la función obtener_primero_y_ultimo
    std::cout << "Ejemplo 1: " << std::get<0>(obtener_primero_y_ultimo({10, 20, 30})) << ", " 
              << std::get<1>(obtener_primero_y_ultimo({10, 20, 30})) << std::endl;  // Debería imprimir (10, 30)
    std::cout << "Ejemplo 2: " << std::get<0>(obtener_primero_y_ultimo({})) << ", " 
              << std::get<1>(obtener_primero_y_ultimo({})) << std::endl;  // Debería imprimir (0, 0)
    std::cout << "Ejemplo 3: " << std::get<0>(obtener_primero_y_ultimo({5})) << ", " 
              << std::get<1>(obtener_primero_y_ultimo({5})) << std::endl;  // Debería imprimir (5, 5)
    std::cout << "Ejemplo 4: " << std::get<0>(obtener_primero_y_ultimo({1, 2, 3, 4, 5})) << ", " 
              << std::get<1>(obtener_primero_y_ultimo({1, 2, 3, 4, 5})) << std::endl;  // Debería imprimir (1, 5)
}

int main() {
    // Asserts para verificar el comportamiento de la función
    assert(obtener_primero_y_ultimo({10, 20, 30}) == std::make_tuple(10, 30));
    // Llamada a la función de ejemplo (no se requiere en los asserts)
    ejemplo_uso();
    
    std::cout << "OK" << std::endl;
    return 0;
}
