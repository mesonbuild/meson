/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright © 2025 Intel Corporation
 */

#ifdef HOST_BUILD
#include "lib.h"
#endif

#include <iostream>
#include <cstring>

namespace {

const char * machine() {
#ifdef HOST_BUILD
    return lib_func();
#else
    return "build";
#endif
}

}

int main() {
    const char * m = machine();
    std::cout << "build for " << m << " machine" << std::endl;
    return std::strcmp(m, FOR_MACHINE) == 0 ? 0 : 1;
}
