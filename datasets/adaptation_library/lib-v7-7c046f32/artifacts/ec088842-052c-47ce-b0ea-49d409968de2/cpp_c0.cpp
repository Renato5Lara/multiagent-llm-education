#include <iostream>
#include <vector>
#include <cassert>

int ejecutar_instrucciones(const std::vector<std::string>& instrucciones) {
    int total = 0;
    for (const auto& instruccion : instrucciones) {
        if (instruccion == "sumar1") {
            total += 1;
        } else if (instruccion == "duplicar") {
            total *= 2;
        }
    }
    return total;
}

int main() {
    assert(ejecutar_instrucciones({"sumar1", "sumar1", "duplicar"}) == 4);
    std::cout << "OK" << std::endl;
    return 0;
}
