#include <iostream>
#include <string>
#include <cassert>

std::string crear_saludo(const std::string& nombre, const std::string& saludo = "Hola") {
    /**
     * Crea un saludo personalizado.
     *
     * Parámetros:
     * nombre (std::string): El nombre de la persona a saludar.
     * saludo (std::string): La frase de saludo. Por defecto es 'Hola'.
     *
     * Retorna:
     * std::string: Un saludo en el formato 'saludo, nombre'.
     */
    // Verificamos si el nombre está vacío
    if (nombre.empty()) {
        return "Nombre no puede estar vacío";
    }
    
    // Retornamos el saludo formateado
    return saludo + ", " + nombre;
}

void ejemplo_uso() {
    // Ejemplo de uso de la función crear_saludo
    std::cout << crear_saludo("Ana") << std::endl;  // Debería imprimir: Hola, Ana
    std::cout << crear_saludo("Ana", "Buenas") << std::endl;  // Debería imprimir: Buenas, Ana
    std::cout << crear_saludo("", "Hola") << std::endl;  // Debería imprimir: Nombre no puede estar vacío
}

int main() {
    // Ejecutamos los asserts para verificar el comportamiento de la función
    assert(crear_saludo("Ana") == "Hola, Ana");
    assert(crear_saludo("Ana", "Buenas") == "Buenas, Ana");
    
    std::cout << "OK" << std::endl;
    return 0;
}
