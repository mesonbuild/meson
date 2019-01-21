#include <iostream>

extern "C" double fortran();

int main(void) {
    std::cout << "FORTRAN gave us this number: " << fortran() << std::endl;
    return EXIT_SUCCESS;
}
