#include <iostream>
#include <cassert>

// Determina si un número es par.
bool es_par(int numero) {
    // Un número es par si el residuo de dividirlo entre 2 es 0
    return numero % 2 == 0;
}

// Calcula cuántas personas pueden recibir una parte exacta del total.
int repartir_exacto(int total, int personas) {
    // La división entera nos da el número de partes exactas que se pueden repartir
    return total / personas;
}

int main() {
    // Verifica si 4 es par
    assert(es_par(4) == true);
    // Verifica si 7 no es par
    assert(es_par(7) == false);
    // Verifica cuántas partes exactas se pueden repartir de 10 entre 3
    assert(repartir_exacto(10, 3) == 3);

    std::cout << "OK" << std::endl;
    return 0;
}
