#include <iostream>
#include <vector>
#include <cassert>

// Función que crea una lista con 4 notas de estudiantes
std::vector<int> crear_lista_de_notas() {
    // Inicializa una lista vacía
    std::vector<int> notas;
    // Agrega la primera nota
    notas.push_back(12);
    // Agrega la segunda nota
    notas.push_back(15);
    // Agrega la tercera nota
    notas.push_back(18);
    // Agrega la cuarta nota
    notas.push_back(9);
    // Devuelve la lista de notas
    return notas;
}

int main() {
    // Verifica que la lista de notas sea la esperada
    assert((crear_lista_de_notas() == std::vector<int>{12, 15, 18, 9}));
    // Si la aserción es correcta, imprime OK
    std::cout << "OK" << std::endl;
    return 0;
}
