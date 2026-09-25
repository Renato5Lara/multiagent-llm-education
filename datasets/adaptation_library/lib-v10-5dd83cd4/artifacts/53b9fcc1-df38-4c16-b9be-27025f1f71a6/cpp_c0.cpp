#include <iostream>
#include <cassert>

int contador_global = 0;

int incrementar_local() {
    int contador_local = 1;
    return contador_local + 1;
}

int incrementar_global() {
    contador_global += 1;
    return contador_global;
}

int main() {
    assert(incrementar_local() == 2);
    assert(incrementar_global() == 1);
    assert(incrementar_global() == 2);
    std::cout << "OK" << std::endl;
    return 0;
}
