#include <iostream>
#include <vector>
#include <string>
#include <cassert>

int ejecutar_instrucciones(const std::vector<std::string>& instrucciones) {
    /**
     * Ejecuta una lista de instrucciones y devuelve el resultado final.
     * 
     * Las instrucciones pueden ser:
     * - "sumar1": suma 1 al resultado actual.
     * - "duplicar": duplica el resultado actual.
     * 
     * Parámetros:
     * instrucciones (vector<string>): Lista de instrucciones a ejecutar.
     * 
     * Retorna:
     * int: Resultado final después de ejecutar todas las instrucciones.
     */
    int resultado = 0;  // Inicializa el resultado en 0
    
    for (const auto& instruccion : instrucciones) {  // Itera sobre cada instrucción
        if (instruccion == "sumar1") {  // Si la instrucción es sumar1
            resultado += 1;  // Suma 1 al resultado
        } else if (instruccion == "duplicar") {  // Si la instrucción es duplicar
            resultado *= 2;  // Duplica el resultado
        }
    }
    
    return resultado;  // Devuelve el resultado final
}

void ejemplo_uso() {
    std::vector<std::string> instrucciones = {"sumar1", "duplicar", "sumar1"};
    int resultado = ejecutar_instrucciones(instrucciones);
    std::cout << "Resultado de ejecutar las instrucciones {\"sumar1\", \"duplicar\", \"sumar1\"}: " << resultado << std::endl;
}

int main() {
    // Ejecuta los asserts para verificar el comportamiento de la función
    assert(ejecutar_instrucciones({"sumar1", "sumar1", "duplicar"}) == 4);
    
    // Muestra un ejemplo de uso
    ejemplo_uso();
    
    std::cout << "OK" << std::endl;
    return 0;
}
