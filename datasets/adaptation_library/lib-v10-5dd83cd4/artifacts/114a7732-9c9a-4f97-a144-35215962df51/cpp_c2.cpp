#include <iostream>
#include <cassert>

bool aprobo(int nota) {
    /**
     * Determina si un estudiante aprueba o no basado en su nota.
     * 
     * Parámetros:
     * nota (int): La nota del estudiante.
     * 
     * Retorna:
     * bool: True si la nota es mayor o igual a 11, False en caso contrario.
     */
    // Verificamos si la nota es un número válido
    if (nota < 0) {  // Caso límite: nota negativa
        return false;
    }
    if (nota > 20) {  // Caso límite: nota excesiva
        return false;
    }
    
    // Comparamos la nota con el umbral de aprobación
    return nota >= 11;  // Retorna true si aprueba, false si no
}

void ejemplo_uso() {
    /**
     * Función que ilustra el uso de la función aprobo.
     */
    std::cout << std::boolalpha; // Para imprimir true/false en lugar de 1/0
    std::cout << aprobo(11) << std::endl;  // Debería imprimir true
    std::cout << aprobo(10) << std::endl;  // Debería imprimir false
    std::cout << aprobo(15) << std::endl;  // Debería imprimir true
    std::cout << aprobo(0) << std::endl;   // Debería imprimir false
    std::cout << aprobo(-5) << std::endl;  // Debería imprimir false
    std::cout << aprobo(25) << std::endl;  // Debería imprimir false
    std::cout << aprobo(0) << std::endl;    // Debería imprimir false
}

int main() {
    assert(aprobo(11) == true);
    assert(aprobo(10) == false);
    
    std::cout << "OK" << std::endl;
    return 0;
}
