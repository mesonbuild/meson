#include <iostream>

int main(void) {
    int* my_int = new int[5];
    my_int[3] = 5;
    delete[] my_int;
    std::cout << my_int[3] << std::endl;
}
