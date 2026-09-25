#include <iostream>
#include <cassert>

bool aprobo(int nota) {
    return nota > 10;
}

int main() {
    assert(aprobo(11) == true);
    assert(aprobo(10) == false);
    std::cout << "OK" << std::endl;
    return 0;
}
