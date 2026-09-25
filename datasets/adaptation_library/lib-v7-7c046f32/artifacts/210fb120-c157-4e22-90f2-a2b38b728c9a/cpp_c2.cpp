#include <iostream>
#include <string>
#include <cassert>

int leer_edad(const std::string& texto_ingresado) {
    /**
     * Convierte un texto ingresado a un entero que representa la edad.
     * 
     * Parámetros:
     * texto_ingresado (std::string): El texto que se desea convertir a un entero.
     * 
     * Retorna:
     * int: La edad como un número entero.
     * 
     * Si el texto ingresado está vacío o no es un número válido, se retorna 0.
     */
    // Verificamos si el texto ingresado está vacío
    if (texto_ingresado.empty()) {
        return 0;  // Retornamos 0 si la entrada está vacía
    }

    try {
        // Intentamos convertir el texto a un entero
        int edad = std::stoi(texto_ingresado);
        
        // Verificamos si la edad es negativa
        if (edad < 0) {
            return 0;  // Retornamos 0 si la edad es negativa
        }
        
        return edad;  // Retornamos la edad válida
    } catch (const std::invalid_argument&) {
        // Si ocurre un error en la conversión, retornamos 0
        return 0;
    } catch (const std::out_of_range&) {
        // Si el número está fuera del rango de int, retornamos 0
        return 0;
    }
}

void ejemplo_uso() {
    // Ejemplo de uso de la función leer_edad
    std::cout << leer_edad("18") << std::endl;  // Debería imprimir 18
    std::cout << leer_edad("25") << std::endl;  // Debería imprimir 25
    std::cout << leer_edad("") << std::endl;     // Debería imprimir 0
    std::cout << leer_edad("-5") << std::endl;   // Debería imprimir 0
    std::cout << leer_edad("abc") << std::endl;  // Debería imprimir 0
}

int main() {
    // Ejecutamos los asserts para verificar el comportamiento de la función
    assert(leer_edad("18") == 18);
    assert(leer_edad("25") == 25);
    
    // Imprimimos OK si todos los asserts pasan
    std::cout << "OK" << std::endl;

    return 0;
}
