#include <iostream>
#include <cassert>

int contador_global = 0; // Se define un contador global

int incrementar_local() {
    // Incrementa un contador local y lo devuelve.
    int contador_local = 0; // Se define un contador local
    contador_local += 1; // Se incrementa el contador local
    contador_local += 1; // Se incrementa nuevamente
    return contador_local; // Se devuelve el valor del contador local
}

int incrementar_global() {
    // Incrementa un contador global y lo devuelve.
    contador_global += 1; // Se incrementa el contador global
    return contador_global; // Se devuelve el valor del contador global
}

int main() {
    // Verifica que incrementar_local() devuelve 2
    assert(incrementar_local() == 2);
    // Verifica que incrementar_global() devuelve 1 en la primera llamada
    assert(incrementar_global() == 1);
    // Verifica que incrementar_global() devuelve 2 en la segunda llamada
    assert(incrementar_global() == 2);
    
    std::cout << "OK" << std::endl; // Imprime OK si todas las aserciones son verdaderas
    return 0; // Fin del programa
}
