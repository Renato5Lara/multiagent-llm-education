#include <iostream>
#include <vector>
#include <cassert>

int primer_multiplo_de_tres(const std::vector<int>& numeros) {
    /*
    Devuelve el primer número múltiplo de tres en la lista de números.
    Si no hay múltiplos de tres, devuelve 0 (equivalente a None en Python).
    
    :param numeros: Lista de números enteros.
    :return: El primer múltiplo de tres encontrado o 0 si no hay.
    */
    for (int numero : numeros) {
        // Si el número es múltiplo de tres, lo devolvemos
        if (numero % 3 == 0) {
            return numero;
        }
        // Si no es múltiplo de tres, continuamos con el siguiente número
        continue;
    }
    // Si no encontramos ningún múltiplo de tres, devolvemos 0
    return 0;
}

std::vector<int> detener_en_negativo(const std::vector<int>& numeros) {
    /*
    Devuelve una lista de números hasta encontrar un número negativo.
    El bucle se detiene al encontrar el primer número negativo.
    
    :param numeros: Lista de números enteros.
    :return: Lista de números hasta el primer negativo (excluido).
    */
    std::vector<int> resultado;
    for (int numero : numeros) {
        // Si encontramos un número negativo, rompemos el bucle
        if (numero < 0) {
            break;
        }
        // Si el número no es negativo, lo añadimos a la lista de resultados
        resultado.push_back(numero);
    }
    return resultado;
}

void ejemplo_uso() {
    /*
    Ejemplo de uso de las funciones primer_multiplo_de_tres y detener_en_negativo.
    */
    // Ejemplo de uso de primer_multiplo_de_tres
    std::vector<int> lista1 = {1, 2, 4, 9};
    int multiplo = primer_multiplo_de_tres(lista1);
    std::cout << "El primer múltiplo de tres en {1, 2, 4, 9} es " << multiplo << std::endl;

    // Ejemplo de uso de detener_en_negativo
    std::vector<int> lista2 = {1, 2, -1, 3};
    std::vector<int> resultado = detener_en_negativo(lista2);
    std::cout << "Los números antes del primer negativo en {1, 2, -1, 3} son {";
    for (size_t i = 0; i < resultado.size(); ++i) {
        std::cout << resultado[i];
        if (i < resultado.size() - 1) {
            std::cout << ", ";
        }
    }
    std::cout << "}" << std::endl;
}

int main() {
    // Asserts para verificar el comportamiento de las funciones
    assert((primer_multiplo_de_tres({1, 2, 4, 9}) == 9));
    assert((detener_en_negativo({1, 2, -1, 3}) == std::vector<int>{1, 2}));

    std::cout << "OK" << std::endl;
    return 0;
}
