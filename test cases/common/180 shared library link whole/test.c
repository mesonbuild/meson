#include "static1.h"
#include "static2.h"
#include "shared.h"

#include <stdio.h>

int main(void) {
    if (meson_test_shared() != 10) {
        printf("bad shared\n");
        return 1;
    }
    if (meson_test_static_1() != 20) {
        printf("bad static1\n");
        return 1;
    }
    if (meson_test_static_2() != 30) {
        printf("bad static2\n");
        return 1;
    }
    return 0;
}
