#include <iostream>
#include <string>
#include <cassert>

double convertir_a_numero(const std::string& texto) {
    /**
     * Convierte una cadena de texto a un número entero o flotante.
     * 
     * Si el texto representa un número entero (sin punto decimal), se convierte a int.
     * Si el texto representa un número decimal (con punto decimal), se convierte a float.
     * 
     * Parámetros:
     * texto (str): La cadena de texto que se desea convertir a número.
     * 
     * Retorna:
     * int o float: El número convertido.
     */
    // Verificamos si el texto está vacío
    if (texto.empty()) {
        return 0;  // Retornamos 0 si la entrada está vacía
    }

    // Intentamos convertir el texto a un número entero
    try {
        size_t pos;
        int numero_entero = std::stoi(texto, &pos);  // Intentamos convertir a int
        if (pos == texto.size()) {
            return numero_entero;  // Retornamos el número entero si la conversión fue exitosa
        }
    } catch (const std::invalid_argument&) {
        // Si falla la conversión a int, intentamos convertir a float
    } catch (const std::out_of_range&) {
        return 0;  // Retornamos 0 si el número está fuera del rango
    }

    // Intentamos convertir a float
    try {
        size_t pos;
        double numero_flotante = std::stod(texto, &pos);  // Intentamos convertir a float
        if (pos == texto.size()) {
            return numero_flotante;  // Retornamos el número flotante si la conversión fue exitosa
        }
    } catch (const std::invalid_argument&) {
        return 0;  // Retornamos 0 si la conversión falla
    } catch (const std::out_of_range&) {
        return 0;  // Retornamos 0 si el número está fuera del rango
    }

    return 0;  // Retornamos 0 si ninguna conversión fue exitosa
}

void ejemplo_uso() {
    // Ejemplo de uso de la función convertir_a_numero
    std::cout << convertir_a_numero("10") << std::endl;  // Debería imprimir 10
    std::cout << convertir_a_numero("3.5") << std::endl;  // Debería imprimir 3.5
    std::cout << convertir_a_numero("") << std::endl;  // Debería imprimir 0
    std::cout << convertir_a_numero("abc") << std::endl;  // Debería imprimir 0
    std::cout << convertir_a_numero("0") << std::endl;  // Debería imprimir 0
    std::cout << convertir_a_numero("1000000000") << std::endl;  // Debería imprimir 1000000000
    std::cout << convertir_a_numero("1.5e10") << std::endl;  // Debería imprimir 15000000000.0
}

int main() {
    // Asserts para verificar el comportamiento de la función
    assert(convertir_a_numero("10") == 10);
    assert(convertir_a_numero("3.5") == 3.5);
    
    std::cout << "OK" << std::endl;
    return 0;
}
