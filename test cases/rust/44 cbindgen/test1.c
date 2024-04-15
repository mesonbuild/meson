/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright © 2024 Intel Corporation
 */

#ifdef USE_LIB2
#include "lib2.h"
#else
#include "lib.h"
#endif

static MyStruct thing = {
    .cost = -5,
    .power = 1,
};

int main() {
    print(&thing);
    return 0;
}
