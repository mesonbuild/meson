#include <iostream>

extern "C" double fortran();

int main(int, char**) {
    std::cout << "FORTRAN gave us this number: " << fortran() << '\n';
    return 0;
}
