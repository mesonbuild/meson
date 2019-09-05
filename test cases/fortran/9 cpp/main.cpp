#include <iostream>

extern "C" double fortran();

int main() {
    std::cout << "FORTRAN gave us this number: " << fortran() << '\n';
    return 0;
}
