/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright © 2024 Intel Corporation
 */

#include "lib3.hpp"

static MyStruct thing = {
    .cost = -5,
    .power = 1,
};

int main() {
    print(&thing);
    return 0;
}
