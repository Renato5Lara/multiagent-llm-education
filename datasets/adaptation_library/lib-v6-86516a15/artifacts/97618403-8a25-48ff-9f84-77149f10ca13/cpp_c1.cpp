#include <iostream>
#include <string>
#include <cassert>

// Función que crea un saludo personalizado para una persona.
std::string crear_saludo(const std::string& nombre, const std::string& saludo = "Hola") {
    // Se forma el saludo combinando el saludo y el nombre
    return saludo + ", " + nombre;
}

int main() {
    // Verificamos que la función devuelve el saludo correcto con el valor por defecto
    assert(crear_saludo("Ana") == "Hola, Ana");
    // Verificamos que la función devuelve el saludo correcto con un saludo personalizado
    assert(crear_saludo("Ana", "Buenas") == "Buenas, Ana");
    
    // Si todas las aserciones son correctas, imprimimos OK
    std::cout << "OK" << std::endl;
    return 0;
}
