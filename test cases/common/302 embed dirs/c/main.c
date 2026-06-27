/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright © 2026 Intel Corporation
 */

#include <stdio.h>

const char msg[] =
{
#embed "data.txt"
};

const char expected[] = {
    'H', 'e', 'l', 'l', 'o', ',', ' ', 'W', 'o', 'r', 'l', 'd', '!', '\n',
};


int main(void) {
    const int num_found = sizeof(msg) / sizeof(msg[0]);
    const int num_expected = sizeof(expected) / sizeof(expected[0]);

    if (num_found != num_expected) {
        fprintf(stderr, "The number of found arguments (%d) does not match the expected(%d)\n", num_found, num_expected);
        return 1;
    }

    for (unsigned i = 0; i < num_found; ++i) {
        if (msg[i] != expected[i]) {
            fprintf(stderr, "The items at index %d does not match: found: %c, expected: %c\n", i, msg[i], expected[i]);
            return 1;
        }
    }

    return 0;
}
