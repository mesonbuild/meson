#include <iostream>
#include <cassert>
#include "common.h"

struct ZLibDependency : Dependency {
    void initialize();
};

void ZLibDependency::initialize() {
    assert(ZLIB);
    std::cout << ANSI_START << "hello from zlib"
              << ANSI_END << std::endl;
}

ZLibDependency zlib;
