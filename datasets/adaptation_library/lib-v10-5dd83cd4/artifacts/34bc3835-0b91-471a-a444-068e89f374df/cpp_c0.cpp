#include <iostream>
#include <cassert>
#include <variant>
#include <string>

std::string describir_tipo(const std::variant<int, double, std::string, bool>& valor) {
    if (std::holds_alternative<int>(valor)) {
        return "int";
    } else if (std::holds_alternative<double>(valor)) {
        return "float";
    } else if (std::holds_alternative<std::string>(valor)) {
        return "str";
    } else if (std::holds_alternative<bool>(valor)) {
        return "bool";
    }
    return "";
}

int main() {
    assert((describir_tipo(5) == "int"));
    assert((describir_tipo(5.0) == "float"));
    assert((describir_tipo(std::string("cinco")) == "str"));
    assert((describir_tipo(true) == "bool"));
    std::cout << "OK" << std::endl;
    return 0;
}
