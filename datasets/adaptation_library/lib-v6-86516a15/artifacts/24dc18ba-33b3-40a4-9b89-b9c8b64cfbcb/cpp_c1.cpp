#include <iostream>
#include <cassert> // Para usar assert

// Función que calcula el promedio ponderado de tres notas
double calcular_promedio_ponderado(double n1, double n2, double n3) {
    // Suma de las notas
    double suma = n1 + n2 + n3;  
    // División de la suma entre 3 para obtener el promedio
    double promedio = suma / 3;  
    // Retorna el promedio calculado
    return promedio;  
}

int main() {
    // Verifica que el promedio ponderado de 10, 10 y 10 sea igual a 10
    assert(calcular_promedio_ponderado(10, 10, 10) == 10);
    std::cout << "OK" << std::endl; // Imprime OK si todas las aserciones son correctas
    return 0; // Fin del programa
}
