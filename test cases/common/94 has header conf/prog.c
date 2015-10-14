#include "config.h"
#ifdef HAVE_STDIO_H
#include <stdio.h>
#else
#error "FAIL!"
#endif

int main(int argc, char **argv) {
    (void) argc;
    (void) argv;
    return 0;
}
