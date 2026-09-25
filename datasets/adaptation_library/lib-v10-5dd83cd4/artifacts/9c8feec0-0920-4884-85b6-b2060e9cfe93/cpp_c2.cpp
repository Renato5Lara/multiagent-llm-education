#include <iostream>
#include <stdexcept>
#include <cassert>

double calcular_iva(double precio) {
    // Calcula el IVA del precio dado.
    // Args:
    //     precio (double): El precio sobre el cual se calculará el IVA.
    // Returns:
    //     double: El monto del IVA calculado.
    // Raises:
    //     std::invalid_argument: Si el precio es negativo.

    // Verificar si el precio es negativo
    if (precio < 0) {
        throw std::invalid_argument("El precio no puede ser negativo.");
    }

    // Definir la tasa de IVA
    const double tasa_iva = 0.18;

    // Calcular el IVA
    double iva = precio * tasa_iva;

    return iva;
}

void ejemplo_uso() {
    // Ejemplo de uso de la función calcular_iva.
    // Ejemplo con un precio de 100
    double precio = 100;
    std::cout << "El IVA de " << precio << " es: " << calcular_iva(precio) << std::endl;
}

int main() {
    // Asserts para verificar el comportamiento de la función calcular_iva
    assert((calcular_iva(100) == 18.0));

    // Imprimir OK si todos los asserts pasan
    std::cout << "OK" << std::endl;

    return 0;
}
