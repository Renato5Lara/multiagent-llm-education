#include <iostream>
#include <vector>
#include <cassert>

std::vector<int> contar_hasta(int n) {
    /**
     * Función que cuenta desde 1 hasta n y devuelve una lista con los números contados.
     * 
     * Parámetros:
     * n (int): El número hasta el cual contar. Debe ser un entero positivo.
     * 
     * Retorna:
     * std::vector<int>: Un vector de enteros desde 1 hasta n.
     */
    // Verificamos si n es menor o igual a 0
    if (n <= 0) {
        return {};  // Retornamos un vector vacío para casos no válidos
    }
    
    // Inicializamos un vector vacío para almacenar los números
    std::vector<int> numeros;
    
    // Usamos un contador para contar desde 1 hasta n
    int contador = 1;
    while (contador <= n) {  // Mientras el contador sea menor o igual a n
        numeros.push_back(contador);  // Agregamos el contador al vector
        contador += 1;  // Incrementamos el contador
    }
    
    return numeros;  // Retornamos el vector con los números contados
}

void ejemplo_uso() {
    /**
     * Función que ilustra el uso de la función contar_hasta.
     */
    std::cout << "Contar hasta 3: ";
    for (int num : contar_hasta(3)) {
        std::cout << num << " ";
    }
    std::cout << std::endl;  // Debería imprimir [1, 2, 3]

    std::cout << "Contar hasta 0: ";
    for (int num : contar_hasta(0)) {
        std::cout << num << " ";
    }
    std::cout << std::endl;  // Debería imprimir []

    std::cout << "Contar hasta -5: ";
    for (int num : contar_hasta(-5)) {
        std::cout << num << " ";
    }
    std::cout << std::endl;  // Debería imprimir []

    std::cout << "Contar hasta 5: ";
    for (int num : contar_hasta(5)) {
        std::cout << num << " ";
    }
    std::cout << std::endl;  // Debería imprimir [1, 2, 3, 4, 5]
}

int main() {
    // Ejecutamos los asserts para verificar el comportamiento de la función
    assert((contar_hasta(3) == std::vector<int>{1, 2, 3}));
    assert((contar_hasta(0) == std::vector<int>{}));
    assert((contar_hasta(-5) == std::vector<int>{}));
    assert((contar_hasta(5) == std::vector<int>{1, 2, 3, 4, 5}));

    std::cout << "OK" << std::endl;  // Imprimimos OK si todos los asserts pasan
    return 0;
}
