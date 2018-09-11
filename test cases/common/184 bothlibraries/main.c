#include <stdlib.h>
#include "mylib.h"

DO_IMPORT int func();
DO_IMPORT int retval;

int main(int argc, char *argv[]) {
    if (func() != retval)
        return 1;

    if (argc > 1 && atoi(argv[1]) != retval)
        return 1;

    return 0;
}
