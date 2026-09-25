#include <iostream>
#include <string>
#include <variant>
#include <cassert>

// Definimos un tipo variante que puede ser int, double, string o bool
using Valor = std::variant<int, double, std::string, bool>;

// Función que clasifica el tipo de dato primitivo de un valor dado
std::string describir_tipo(const Valor& valor) {
    // Se utiliza std::holds_alternative para determinar el tipo
    if (std::holds_alternative<int>(valor)) {
        return "int"; // Si es int, devolvemos "int"
    } else if (std::holds_alternative<double>(valor)) {
        return "float"; // Si es double, devolvemos "float"
    } else if (std::holds_alternative<std::string>(valor)) {
        return "str"; // Si es string, devolvemos "str"
    } else if (std::holds_alternative<bool>(valor)) {
        return "bool"; // Si es bool, devolvemos "bool"
    }
    return ""; // En caso de que no coincida con ningún tipo, devolvemos una cadena vacía
}

int main() {
    // Realizamos los asserts para verificar el comportamiento de la función
    assert((describir_tipo(5) == std::string("int"))); // Verificamos que 5 es int
    assert((describir_tipo(5.0) == std::string("float"))); // Verificamos que 5.0 es float
    assert((describir_tipo(std::string("cinco")) == std::string("str"))); // Verificamos que "cinco" es str
    assert((describir_tipo(true) == std::string("bool"))); // Verificamos que true es bool

    std::cout << "OK" << std::endl; // Imprimimos OK si todos los asserts pasan
    return 0; // Retornamos 0 para indicar que el programa finalizó correctamente
}
