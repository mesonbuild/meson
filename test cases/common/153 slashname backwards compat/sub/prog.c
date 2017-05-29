#include<stdio.h>

#include "rootsrcdir.h"

#ifndef MESON_MUST_BE_DEFINED
#error "Not defined"
#endif

int main(int argc, char **argv) {
    printf("ok\n");
    return 1;
}
