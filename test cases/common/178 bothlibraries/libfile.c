#include "mylib.h"

#ifndef TEST_VAL
#define TEST_VAL 42
#endif

DO_EXPORT int retval = TEST_VAL;

DO_EXPORT int func(void) {
    return retval;
}
