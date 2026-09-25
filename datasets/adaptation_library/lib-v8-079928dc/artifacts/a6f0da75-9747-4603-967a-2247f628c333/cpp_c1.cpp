#include <iostream>
#include <cassert>

// Función que suma los números del 1 al n.
int suma_hasta(int n) {
    // Inicializa el total en 0
    int total = 0;  
    // Itera desde 1 hasta n
    for (int i = 1; i <= n; ++i) {  
        // Suma el valor actual de i al total
        total += i;  
    }
    // Devuelve el total acumulado
    return total;  
}

int main() {
    // Verifica que la suma de los números del 1 al 5 sea 15
    assert(suma_hasta(5) == 15);
    // Verifica que la suma de los números del 1 al 1 sea 1
    assert(suma_hasta(1) == 1);
    
    // Si todas las aserciones son correctas, imprime OK
    std::cout << "OK" << std::endl;
    return 0;
}
