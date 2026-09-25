#include <iostream>
#include <cassert>
#include <limits>

float calcular_promedio_ponderado(float n1, float n2, float n3) {
    /**
     * Calcula el promedio ponderado de tres notas.
     * 
     * Parámetros:
     * n1 (float): Primera nota.
     * n2 (float): Segunda nota.
     * n3 (float): Tercera nota.
     * 
     * Retorna:
     * float: El promedio ponderado de las tres notas.
     * 
     * Nota: Los paréntesis alrededor de (n1 + n2 + n3) son necesarios para asegurar que la suma se realice antes de la división.
     * Sin los paréntesis, la división podría ocurrir antes de la suma, alterando el resultado final.
     */
    // Verificar si las notas son válidas (no vacías y no negativas)
    if (n1 < 0 || n2 < 0 || n3 < 0) {
        return std::numeric_limits<float>::quiet_NaN(); // Retorna NaN si alguna nota es negativa
    }

    // Calcular el promedio ponderado
    float total_notas = n1 + n2 + n3; // Sumar las notas
    float promedio = total_notas / 3;  // Dividir la suma entre 3 para obtener el promedio
    return promedio; // Retornar el promedio calculado
}

void ejemplo_uso() {
    std::cout << calcular_promedio_ponderado(10, 10, 10) << std::endl;  // Debería imprimir 10.0
    std::cout << calcular_promedio_ponderado(0, 0, 0) << std::endl;      // Debería imprimir 0.0
    std::cout << calcular_promedio_ponderado(5, 10, 15) << std::endl;    // Debería imprimir 10.0
    std::cout << calcular_promedio_ponderado(std::numeric_limits<float>::quiet_NaN(), 10, 10) << std::endl; // Debería imprimir NaN
    std::cout << calcular_promedio_ponderado(-1, 10, 10) << std::endl;   // Debería imprimir NaN
}

int main() {
    assert(calcular_promedio_ponderado(10, 10, 10) == 10.0f);
    std::cout << "OK" << std::endl;
    return 0;
}
