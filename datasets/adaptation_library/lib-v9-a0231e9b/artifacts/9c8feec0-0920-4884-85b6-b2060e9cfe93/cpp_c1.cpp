#include <iostream>
#include <cassert>

// Definición de la función calcular_iva
double calcular_iva(double precio) {
    // Calcula el IVA del precio dado
    double iva = precio * 0.18;  // Calcula el 18% del precio
    return iva;  // Devuelve el valor del IVA
}

int main() {
    // Invocación de la función calcular_iva
    double total = calcular_iva(100);

    // Afirmaciones para verificar el comportamiento de la función
    assert((calcular_iva(100) == 18.0));

    // Imprime OK si todas las afirmaciones son correctas
    std::cout << "OK" << std::endl;
    return 0;
}
