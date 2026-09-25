#include <iostream>
#include <vector>
#include <cassert>

// Función que cuenta desde 1 hasta n y devuelve una lista con los números.
std::vector<int> contar_hasta(int n) {
    int contador = 1;  // Inicializa el contador en 1
    std::vector<int> numeros;  // Vector para almacenar los números contados
    while (contador <= n) {  // Mientras el contador sea menor o igual a n
        numeros.push_back(contador);  // Agrega el contador al vector
        contador += 1;  // Incrementa el contador en 1
    }
    return numeros;  // Devuelve el vector de números contados
}

int main() {
    // Asegúrate de que la función funciona correctamente
    assert((contar_hasta(3) == std::vector<int>{1, 2, 3}));
    std::cout << "OK" << std::endl;  // Imprime OK si todos los asserts pasan
    return 0;  // Fin del programa
}
