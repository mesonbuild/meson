#include "meson_test_function.h"

#include <stdio.h>

int main() {
    if (meson_test_function() != 19) {
        printf("Bad meson_test_function()\n");
        return 1;
    }
    return 0;
}
