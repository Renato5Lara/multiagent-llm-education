#include <iostream>
#include <tuple>
#include <cassert>

std::tuple<int, int> dividir_con_resto(int a, int b) {
    return std::make_tuple(a / b, a % b);
}

int main() {
    assert(dividir_con_resto(10, 3) == std::make_tuple(3, 1));
    std::cout << "OK" << std::endl;
    return 0;
}
