/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright © 2026 Intel Corporation
 */

#include <iostream>

constexpr char msg[] =
{
#embed "data.txt"
};

constexpr char expected[] = {
    'H', 'e', 'l', 'l', 'o', ',', ' ', 'W', 'o', 'r', 'l', 'd', '!', '\n',
};


int main(void) {
    constexpr int num_found = sizeof(msg) / sizeof(msg[0]);
    constexpr int num_expected = sizeof(expected) / sizeof(expected[0]);

    if (num_found != num_expected) {
        std::cerr << "The number of found arguments (" << num_found << ") does not match the expected (" << num_expected << ")\n";
        return 1;
    }

    for (unsigned i = 0; i < num_found; ++i) {
        if (msg[i] != expected[i]) {
            std::cerr << "The items at index " << i << "does not match: found: " << msg[i] << "expected: " << expected[i] << "\n";
            return 1;
        }
    }

    return 0;
}
