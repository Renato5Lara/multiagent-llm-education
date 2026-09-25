#include <iostream>
#include <vector>
#include <cassert>

// Función que encuentra el mayor número en una lista de números
int encontrar_mayor(const std::vector<int>& numeros) {
    // Tomar el primer número como candidato inicial
    int mayor = numeros[0];
    
    // Recorrer la lista de números
    for (int numero : numeros) {
        // Comparar el número actual con el candidato
        if (numero > mayor) {
            // Actualizar el candidato si se encuentra un número mayor
            mayor = numero;
        }
    }
    
    // Devolver el mayor número encontrado
    return mayor;
}

int main() {
    // Afirmaciones para verificar el funcionamiento de la función
    assert(encontrar_mayor({3, 7, 2}) == 7);
    assert(encontrar_mayor({-1, -5, -2}) == -1);
    
    // Imprimir OK si todas las afirmaciones son correctas
    std::cout << "OK" << std::endl;
    return 0;
}
