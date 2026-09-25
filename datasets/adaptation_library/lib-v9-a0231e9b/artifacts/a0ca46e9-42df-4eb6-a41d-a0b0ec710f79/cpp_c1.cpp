#include <iostream>
#include <vector>
#include <algorithm>
#include <cassert>

std::vector<int> actualizar_lista(std::vector<int> lista) {
    // Agrega el número 40 al final de la lista
    lista.push_back(40);  // [10, 20, 30, 40]
    
    // Inserta el número 5 al inicio de la lista
    lista.insert(lista.begin(), 5);  // [5, 10, 20, 30, 40]
    
    // Elimina el número 20 de la lista
    lista.erase(std::remove(lista.begin(), lista.end(), 20), lista.end());  // [5, 10, 30, 40]
    
    // Elimina el último elemento de la lista
    lista.pop_back();  // [5, 10, 30]
    
    return lista;
}

int main() {
    // Verifica que la función actualiza la lista correctamente
    assert((actualizar_lista({10, 20, 30}) == std::vector<int>{5, 10, 30}));
    std::cout << "OK" << std::endl;
    return 0;
}
