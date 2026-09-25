#include <iostream>
#include <cassert>

// Función que determina si un número es par
bool es_par(int numero) {
    /*
    Determina si un número es par.

    Un número es par si es divisible por 2 sin residuo.

    Parámetros:
    numero (int): El número a evaluar.

    Retorna:
    bool: True si el número es par, False si es impar.
    */
    // Verificamos si el número es divisible por 2
    return numero % 2 == 0;
}

// Función que calcula cuántas personas pueden recibir una parte exacta de un total
int repartir_exacto(int total, int personas) {
    /*
    Calcula cuántas personas pueden recibir una parte exacta de un total.

    Realiza la división entera del total entre el número de personas.

    Parámetros:
    total (int): La cantidad total a repartir.
    personas (int): El número de personas entre las que se reparte.

    Retorna:
    int: La cantidad entera que recibe cada persona.
    */
    // Verificamos si el número de personas es cero para evitar división por cero
    if (personas == 0) {
        return 0;  // No se puede repartir entre cero personas
    }
    // Realizamos la división entera
    return total / personas;
}

// Función que muestra ejemplos de uso
void ejemplo_uso() {
    std::cout << std::boolalpha; // Para imprimir bool como true/false
    std::cout << es_par(4) << std::endl;  // Debería imprimir true
    std::cout << es_par(7) << std::endl;  // Debería imprimir false
    std::cout << repartir_exacto(10, 3) << std::endl;  // Debería imprimir 3
    std::cout << repartir_exacto(10, 0) << std::endl;  // Debería imprimir 0
}

int main() {
    // Ejecutamos los asserts para verificar el comportamiento de las funciones
    assert(es_par(4) == true);
    assert(es_par(7) == false);
    assert(repartir_exacto(10, 3) == 3);

    std::cout << "OK" << std::endl; // Imprimimos OK si todos los asserts pasan
    return 0;
}
