#include <iostream>
#include <cassert>

bool puede_matricularse(bool tiene_requisitos, bool sin_deuda) {
    return tiene_requisitos && sin_deuda;
}

int main() {
    assert(puede_matricularse(true, true) == true);
    assert(puede_matricularse(true, false) == false);
    std::cout << "OK" << std::endl;
    return 0;
}
