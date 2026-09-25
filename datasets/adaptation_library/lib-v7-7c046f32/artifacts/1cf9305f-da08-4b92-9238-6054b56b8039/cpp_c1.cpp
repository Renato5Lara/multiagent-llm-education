#include <iostream>
#include <vector>
#include <cassert>

double procesar_promedio(const std::vector<int>& notas) {
    // Sumar todas las notas
    double suma = 0;
    for (int nota : notas) {
        suma += nota;
    }
    
    // Contar la cantidad de notas
    int cantidad = notas.size();
    
    // Calcular el promedio
    double promedio = suma / cantidad;
    
    // Retornar el promedio calculado
    return promedio;
}

int main() {
    // Verificar que el promedio de [10, 20, 30] sea 20
    assert(procesar_promedio({10, 20, 30}) == 20);
    
    std::cout << "OK" << std::endl;
    return 0;
}
