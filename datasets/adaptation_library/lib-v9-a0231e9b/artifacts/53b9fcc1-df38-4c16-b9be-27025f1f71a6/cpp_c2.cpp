#include <iostream>
#include <cassert>

int contador_global = 0; // Contador global que persiste entre llamadas

int incrementar_local() {
    /** Incrementa un contador local y lo devuelve.
    
    Este contador se reinicia en cada llamada a la función.
    */
    int contador_local = 1; // Inicializa el contador local
    contador_local += 1; // Incrementa el contador local
    return contador_local; // Devuelve el valor del contador local
}

int incrementar_global() {
    /** Incrementa un contador global y lo devuelve.
    
    Este contador persiste entre llamadas a la función.
    */
    contador_global += 1; // Incrementa el contador global
    return contador_global; // Devuelve el valor del contador global
}

void ejemplo_uso() {
    /** Ejemplo de uso de las funciones incrementar_local e incrementar_global. */
    std::cout << incrementar_local() << std::endl; // Debería imprimir 2
    std::cout << incrementar_global() << std::endl; // Debería imprimir 1
    std::cout << incrementar_global() << std::endl; // Debería imprimir 2
}

int main() {
    // Ejecutar los asserts para verificar el comportamiento de las funciones
    assert(incrementar_local() == 2);
    assert(incrementar_global() == 1);
    assert(incrementar_global() == 2);
    
    std::cout << "OK" << std::endl; // Imprimir OK si todos los asserts pasan
    return 0;
}
