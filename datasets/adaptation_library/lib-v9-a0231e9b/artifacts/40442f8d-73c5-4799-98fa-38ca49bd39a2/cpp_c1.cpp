#include <iostream>
#include <vector>
#include <cassert>

// Devuelve el primer número múltiplo de tres en la lista de números.
// Si se encuentra un múltiplo de tres, se termina el bucle.
int primer_multiplo_de_tres(const std::vector<int>& numeros) {
    for (int numero : numeros) {
        // Verifica si el número es múltiplo de tres
        if (numero % 3 == 0) {
            return numero;  // Termina el bucle y devuelve el número
        }
        // Si no es múltiplo de tres, continúa con el siguiente número
        continue;
    }
    return -1; // Retorna -1 si no se encuentra ningún múltiplo de tres
}

// Devuelve una lista de números hasta encontrar un número negativo.
// Si se encuentra un número negativo, se termina el bucle.
std::vector<int> detener_en_negativo(const std::vector<int>& numeros) {
    std::vector<int> resultado; // Vector para almacenar los resultados
    for (int numero : numeros) {
        // Verifica si el número es negativo
        if (numero < 0) {
            break;  // Termina el bucle si el número es negativo
        }
        resultado.push_back(numero);  // Agrega el número a la lista de resultados
    }
    return resultado; // Retorna la lista de resultados
}

int main() {
    // Afirmaciones para verificar el comportamiento de las funciones
    assert((primer_multiplo_de_tres({1, 2, 4, 9}) == 9));
    assert((detener_en_negativo({1, 2, -1, 3}) == std::vector<int>{1, 2}));
    
    std::cout << "OK" << std::endl; // Imprime OK si todas las afirmaciones son verdaderas
    return 0; // Fin del programa
}
