#include <iostream>
#include <vector>
#include <string>
#include <cassert>

// Función que ejecuta una lista de instrucciones y devuelve el resultado final.
int ejecutar_instrucciones(const std::vector<std::string>& instrucciones) {
    int resultado = 0;  // Inicializa el resultado en 0
    
    // Itera sobre cada instrucción
    for (const auto& instruccion : instrucciones) {
        // Si la instrucción es sumar1
        if (instruccion == "sumar1") {
            resultado += 1;  // Suma 1 al resultado
        }
        // Si la instrucción es duplicar
        else if (instruccion == "duplicar") {
            resultado *= 2;  // Duplica el resultado
        }
    }
    
    return resultado;  // Devuelve el resultado final
}

int main() {
    // Verifica que el resultado de ejecutar las instrucciones sea el esperado
    assert(ejecutar_instrucciones({"sumar1", "sumar1", "duplicar"}) == 4);
    
    std::cout << "OK" << std::endl;  // Imprime OK si todas las aserciones son correctas
    return 0;  // Finaliza el programa
}
