#include <iostream>
#include <string>
#include <variant>
#include <cassert>

using Valor = std::variant<int, double, std::string, bool>;

std::string describir_tipo(const Valor& valor) {
    /**
     * Clasifica el tipo de dato primitivo del valor proporcionado.
     * 
     * Parámetros:
     * valor: El valor cuyo tipo de dato se desea clasificar.
     * 
     * Retorna:
     * str: Una cadena que representa el tipo de dato primitivo del valor.
     */
    // Verificar si el valor es de tipo entero
    if (std::holds_alternative<int>(valor)) {
        // Caso especial: True y False son instancias de int en Python
        int intValue = std::get<int>(valor);
        if (intValue == 1 || intValue == 0) { // 1 es True, 0 es False
            return "bool";
        }
        return "int";
    }
    // Verificar si el valor es de tipo flotante
    else if (std::holds_alternative<double>(valor)) {
        return "float";
    }
    // Verificar si el valor es de tipo cadena
    else if (std::holds_alternative<std::string>(valor)) {
        return "str";
    }
    // Verificar si el valor es de tipo booleano
    else if (std::holds_alternative<bool>(valor)) {
        return "bool";
    }
    // Si el tipo de dato no es reconocido, retornar None
    return "";
}

void ejemplo_uso() {
    /**
     * Muestra ejemplos de uso de la función describir_tipo.
     */
    // Ejemplos de uso de la función describir_tipo
    std::cout << describir_tipo(Valor(5)) << std::endl;      // Debería imprimir "int"
    std::cout << describir_tipo(Valor(5.0)) << std::endl;    // Debería imprimir "float"
    std::cout << describir_tipo(Valor(std::string("cinco"))) << std::endl; // Debería imprimir "str"
    std::cout << describir_tipo(Valor(true)) << std::endl;   // Debería imprimir "bool"
}

int main() {
    assert((describir_tipo(Valor(5)) == "int"));
    assert((describir_tipo(Valor(5.0)) == "float"));
    assert((describir_tipo(Valor(std::string("cinco"))) == "str"));
    assert((describir_tipo(Valor(true)) == "bool"));

    std::cout << "OK" << std::endl;
    return 0;
}
