#include <iostream>
#include <tuple>
#include <cassert>

std::tuple<int, int> dividir_con_resto(int a, int b) {
    /**
     * Divide dos números y retorna el cociente y el resto.
     *
     * Parámetros:
     * a (int): El numerador.
     * b (int): El denominador.
     *
     * Retorna:
     * tuple: Una tupla que contiene el cociente y el resto de la división.
     */
    // Manejo de caso límite: si el denominador es cero
    if (b == 0) {
        throw std::invalid_argument("El denominador no puede ser cero.");
    }
    
    // Cálculo del cociente
    int cociente = a / b;
    
    // Cálculo del resto
    int resto = a % b;
    
    // Retorno de una tupla con el cociente y el resto
    return std::make_tuple(cociente, resto);
}

void ejemplo_uso() {
    // Ejemplo de uso de la función dividir_con_resto
    auto resultado = dividir_con_resto(10, 3);
    std::cout << "El cociente y resto de 10 dividido por 3 son: (" 
              << std::get<0>(resultado) << ", " 
              << std::get<1>(resultado) << ")" << std::endl;
}

int main() {
    // Asserts para verificar el comportamiento de la función
    assert(dividir_con_resto(10, 3) == std::make_tuple(3, 1));
    
    std::cout << "OK" << std::endl;
    return 0;
}
