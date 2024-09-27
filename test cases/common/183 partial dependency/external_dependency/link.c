/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright © 2024 Intel Corporation
 */

#include <zlib.h>
#include <string.h>

int main(void) {
    const char * zver = zlibVersion();
    return strcmp(zver, ZLIB_VERSION);
}
