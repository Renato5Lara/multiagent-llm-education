#include <iostream>
#include <cassert>

int actualizar_saldo(int saldo_inicial, int deposito) {
    int saldo = saldo_inicial;
    saldo += deposito;
    return saldo;
}

int main() {
    assert((actualizar_saldo(100, 50) == 150));
    std::cout << "OK" << std::endl;
    return 0;
}
