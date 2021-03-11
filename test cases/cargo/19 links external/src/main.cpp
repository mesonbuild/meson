#include <iostream>

#include <zstd.h>

int main() {
    std::cout << "ZSTD maximum compression level is: " << ZSTD_maxCLevel() << std::endl;
    return 0;
}