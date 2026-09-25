#include <iostream>
#include <string>
#include <cassert>

std::string clasificar_nota(float nota) {
    /**
     * Clasifica la nota en 'excelente' o 'regular'.
     * 
     * Parámetros:
     * nota (float): La nota a clasificar.
     * 
     * Retorna:
     * str: 'excelente' si la nota es mayor o igual a 17, 'regular' en caso contrario.
     */
    // Verificamos si la nota es un número válido
    if (nota < 0 || nota > 20) {
        return "Entrada no válida"; // Consideramos notas fuera del rango 0-20 como inválidas
    }
    
    // Clasificamos la nota
    if (nota >= 17) {  // Si la nota es mayor o igual a 17
        return "excelente";  // Retornamos 'excelente'
    } else {  // En caso contrario
        return "regular";  // Retornamos 'regular'
    }
}

void ejemplo_uso() {
    // Ejemplo de uso de la función clasificar_nota
    std::cout << clasificar_nota(18) << std::endl;  // Debería imprimir 'excelente'
    std::cout << clasificar_nota(12) << std::endl;  // Debería imprimir 'regular'
}

int main() {
    // Ejecutamos los asserts para verificar el comportamiento de la función
    assert(clasificar_nota(18) == "excelente");
    assert(clasificar_nota(12) == "regular");
    
    std::cout << "OK" << std::endl; // Imprimimos OK si todos los asserts pasan
    return 0;
}
