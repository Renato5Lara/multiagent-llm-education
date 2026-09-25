#include <iostream>
#include <vector>
#include <cassert>

int primer_multiplo_de_tres(const std::vector<int>& numeros) {
    for (int numero : numeros) {
        if (numero % 3 != 0) {
            continue;
        }
        return numero;
    }
    return -1; // Valor por defecto si no se encuentra un múltiplo de 3
}

std::vector<int> detener_en_negativo(const std::vector<int>& numeros) {
    std::vector<int> resultado;
    for (int numero : numeros) {
        if (numero < 0) {
            break;
        }
        resultado.push_back(numero);
    }
    return resultado;
}

int main() {
    assert((primer_multiplo_de_tres({1, 2, 4, 9}) == 9));
    assert((detener_en_negativo({1, 2, -1, 3}) == std::vector<int>{1, 2}));
    std::cout << "OK" << std::endl;
    return 0;
}
