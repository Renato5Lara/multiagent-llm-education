#include <iostream>
#include <tuple>
#include <cassert>

// Función que devuelve el cociente y el resto de la división de a entre b.
std::tuple<int, int> dividir_con_resto(int a, int b) {
    // Calcula el cociente de la división entera
    int cociente = a / b;  
    // Calcula el resto de la división
    int resto = a % b;     
    // Retorna una tupla con cociente y resto
    return std::make_tuple(cociente, resto);  
}

int main() {
    // Verifica que la función devuelve el resultado esperado
    assert(dividir_con_resto(10, 3) == std::make_tuple(3, 1));
    std::cout << "OK" << std::endl; // Imprime OK si todos los asserts pasan
    return 0;
}
