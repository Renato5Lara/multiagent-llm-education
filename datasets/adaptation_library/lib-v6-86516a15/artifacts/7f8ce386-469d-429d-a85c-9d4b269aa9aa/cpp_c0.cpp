#include <iostream>
#include <vector>
#include <string>
#include <cassert>

int buscar_estudiante(const std::vector<std::string>& lista, const std::string& nombre) {
    for (const auto& estudiante : lista) {
        if (estudiante == nombre) {
            return &estudiante - &lista[0];
        }
    }
    return -1;
}

int main() {
    assert(buscar_estudiante({"Ana", "Luis"}, "Luis") == 1);
    assert(buscar_estudiante({"Ana", "Luis"}, "Marco") == -1);
    std::cout << "OK" << std::endl;
    return 0;
}
