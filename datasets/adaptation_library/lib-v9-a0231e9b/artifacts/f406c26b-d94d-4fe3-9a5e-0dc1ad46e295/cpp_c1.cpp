#include <iostream>
#include <cassert>

int actualizar_saldo(int saldo_inicial, int deposito) {
    // 'saldo' inicialmente tiene el valor de 'saldo_inicial'
    int saldo = saldo_inicial;
    
    // Se añade 'deposito' al 'saldo'
    saldo += deposito;
    
    // Retorna el nuevo valor de 'saldo'
    return saldo;
}

int main() {
    // Verificamos que la función actualiza el saldo correctamente
    assert((actualizar_saldo(100, 50) == 150));
    
    std::cout << "OK" << std::endl;
    return 0;
}
