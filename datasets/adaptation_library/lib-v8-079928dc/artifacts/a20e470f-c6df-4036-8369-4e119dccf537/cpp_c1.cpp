#include <iostream>
#include <string>
#include <cassert>

// Función que convierte un texto a un número entero o flotante según su formato.
double convertir_a_numero(const std::string& texto) {
    // Verifica si hay un punto decimal en el texto
    if (texto.find('.') != std::string::npos) {
        // Convierte a float si hay punto decimal
        return std::stod(texto); // std::stod convierte string a double
    } else {
        // Convierte a int si no hay punto decimal
        return std::stoi(texto); // std::stoi convierte string a int
    }
}

int main() {
    // Afirmaciones para verificar el comportamiento de la función
    assert(convertir_a_numero("10") == 10);
    assert(convertir_a_numero("3.5") == 3.5);
    
    // Imprime OK si todas las afirmaciones son verdaderas
    std::cout << "OK" << std::endl;
    return 0;
}
