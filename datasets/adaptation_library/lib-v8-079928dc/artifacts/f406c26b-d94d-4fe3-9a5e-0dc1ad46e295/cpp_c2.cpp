#include <iostream>
#include <cassert>

float actualizar_saldo(float saldo_inicial, float deposito) {
    /**
     * Actualiza el saldo inicial sumando un depósito.
     * 
     * Parámetros:
     * saldo_inicial (float): El saldo inicial de la cuenta.
     * deposito (float): La cantidad de dinero a depositar.
     * 
     * Retorna:
     * float: El nuevo saldo después de realizar el depósito.
     */
    
    // Verificamos si el saldo inicial es un número válido
    if (saldo_inicial != saldo_inicial || deposito != deposito) {
        return -1; // Error: saldo inicial o depósito no pueden ser NaN
    }
    
    // Verificamos si el saldo inicial y el depósito son números
    if ((saldo_inicial < -1e10 || saldo_inicial > 1e10) || (deposito < -1e10 || deposito > 1e10)) {
        return -1; // Error: saldo inicial y depósito deben ser números
    }
    
    // Verificamos si el saldo inicial es negativo
    if (saldo_inicial < 0) {
        return -1; // Error: saldo inicial no puede ser negativo
    }
    
    // Verificamos si el depósito es negativo
    if (deposito < 0) {
        return -1; // Error: el depósito no puede ser negativo
    }
    
    // Antes de la suma
    float saldo = saldo_inicial;
    // Aquí el saldo es igual a saldo_inicial
    // Ahora sumamos el depósito al saldo
    saldo += deposito;
    // Después de la suma
    // Aquí el saldo es igual a saldo_inicial + deposito
    return saldo;
}

void ejemplo_uso() {
    float saldo_inicial = 100;
    float deposito = 50;
    float nuevo_saldo = actualizar_saldo(saldo_inicial, deposito);
    std::cout << "Saldo inicial: " << saldo_inicial << ". Después de la suma: " << nuevo_saldo << "." << std::endl;
}

int main() {
    assert((actualizar_saldo(100, 50) == 150));
    std::cout << "OK" << std::endl;
    return 0;
}
