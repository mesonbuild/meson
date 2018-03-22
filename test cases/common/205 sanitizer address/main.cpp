#include <iostream>

#include "lib.h"

int main(void) {
    int* my_int = new int[5];
    my_int[3] = 5;
    std::cout << my_int[3] << std::endl;
    fun(my_int);
}
