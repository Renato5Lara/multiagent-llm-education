#include <iostream>
#include <cassert>

int suma_hasta(int n) {
    /*
    Suma todos los números enteros desde 1 hasta n.

    Parámetros:
    n (int): El número hasta el cual se sumarán los enteros.

    Retorna:
    int: La suma de los números desde 1 hasta n. Si n es menor que 1, retorna 0.
    */
    // Verificamos si n es menor que 1
    if (n < 1) {
        return 0;  // Retornamos 0 si n es menor que 1
    }

    int total = 0;  // Inicializamos la variable total en 0
    // Iteramos desde 1 hasta n (inclusive)
    for (int i = 1; i <= n; ++i) {
        total += i;  // Sumamos el valor actual de i al total
    }

    return total;  // Retornamos el total acumulado
}

void ejemplo_uso() {
    std::cout << suma_hasta(5) << std::endl;  // Debería imprimir 15
    std::cout << suma_hasta(1) << std::endl;  // Debería imprimir 1
    std::cout << suma_hasta(0) << std::endl;  // Debería imprimir 0
    std::cout << suma_hasta(-3) << std::endl; // Debería imprimir 0
}

int main() {
    // Ejecutamos los asserts para verificar el comportamiento de la función
    assert(suma_hasta(5) == 15);
    assert(suma_hasta(1) == 1);
    
    // Llamamos a ejemplo_uso para mostrar el uso de la función
    ejemplo_uso();
    
    std::cout << "OK" << std::endl; // Imprimimos OK si todo está correcto
    return 0;
}
