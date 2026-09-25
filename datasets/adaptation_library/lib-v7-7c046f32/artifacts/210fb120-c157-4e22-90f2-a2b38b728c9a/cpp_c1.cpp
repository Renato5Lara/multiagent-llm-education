#include <iostream>
#include <string>
#include <cassert>

// Convierte un texto ingresado a un número entero que representa la edad.
int leer_edad(const std::string& texto_ingresado) {
    // Convierte el texto ingresado a un entero
    int edad = std::stoi(texto_ingresado);
    return edad; // Devuelve la edad como un número entero
}

int main() {
    // Verifica que la función leer_edad funcione correctamente
    assert(leer_edad("18") == 18);
    assert(leer_edad("25") == 25);
    
    // Si todas las aserciones son correctas, imprime OK
    std::cout << "OK" << std::endl;
    return 0;
}
