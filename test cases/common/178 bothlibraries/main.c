#include "mylib.h"

DO_IMPORT int func(void);

#ifndef TEST_VAL
DO_IMPORT int retval;
#else
static int retval = TEST_VAL;
#endif


int main(void) {
    return func() == retval ? 0 : 1;
}
