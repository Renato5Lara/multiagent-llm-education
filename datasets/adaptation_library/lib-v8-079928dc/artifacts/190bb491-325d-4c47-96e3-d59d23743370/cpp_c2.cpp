#include <iostream>
#include <vector>
#include <cassert>

std::vector<int> crear_lista_de_notas() {
    /** Crea una lista con 4 notas de estudiantes en el orden en que fueron registradas. */
    // Inicializamos la lista de notas
    std::vector<int> notas;
    
    // Agregamos las notas a la lista
    notas.push_back(12);  // Primera nota
    notas.push_back(15);  // Segunda nota
    notas.push_back(18);  // Tercera nota
    notas.push_back(9);   // Cuarta nota
    
    // Retornamos la lista de notas
    return notas;
}

void ejemplo_uso() {
    /** Ejemplo de uso de la función crear_lista_de_notas. */
    // Llamamos a la función y almacenamos el resultado
    std::vector<int> lista_de_notas = crear_lista_de_notas();
    
    // Imprimimos la lista de notas
    std::cout << "[";
    for (size_t i = 0; i < lista_de_notas.size(); ++i) {
        std::cout << lista_de_notas[i];
        if (i < lista_de_notas.size() - 1) {
            std::cout << ", ";
        }
    }
    std::cout << "]" << std::endl;  // Debería mostrar: [12, 15, 18, 9]
}

int main() {
    // Asserts para verificar el comportamiento de la función
    assert((crear_lista_de_notas() == std::vector<int>{12, 15, 18, 9}));

    // Ejemplo de uso
    ejemplo_uso();

    std::cout << "OK" << std::endl;
    return 0;
}
