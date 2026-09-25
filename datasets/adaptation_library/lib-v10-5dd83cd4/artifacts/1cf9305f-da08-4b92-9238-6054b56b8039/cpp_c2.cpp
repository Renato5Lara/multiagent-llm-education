#include <iostream>
#include <vector>
#include <cassert>

float procesar_promedio(const std::vector<float>& notas) {
    /*
    Calcula el promedio de una lista de notas.

    Parámetros:
    notas (vector<float>): Lista de números que representan las notas.

    Retorna:
    float: El promedio de las notas. Si la lista está vacía, retorna 0.
    */
    // Paso 1: Verificar si la lista de notas está vacía
    if (notas.empty()) {
        return 0;  // Si está vacía, retornar 0
    }

    // Paso 2: Calcular la suma de las notas
    float suma_notas = 0;  // Inicializar la suma
    for (const auto& nota : notas) {
        suma_notas += nota;  // Sumar todas las notas
    }

    // Paso 3: Calcular el promedio dividiendo la suma entre la cantidad de notas
    float promedio = suma_notas / notas.size();  // Dividir la suma por el número de notas
    return promedio;  // Retornar el promedio calculado
}

void ejemplo_uso() {
    std::cout << procesar_promedio({10, 20, 30}) << std::endl;  // Ejemplo de uso de la función procesar_promedio
}

int main() {
    // Ejecutar asserts para verificar el comportamiento de la función
    assert(procesar_promedio({10, 20, 30}) == 20);
    
    std::cout << "OK" << std::endl;  // Imprimir OK si todos los asserts pasan
    return 0;
}
