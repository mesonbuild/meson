#include "mylib.h"

#ifdef STATIC_COMPILATION
DO_EXPORT int retval = 42;
#else
DO_EXPORT int retval = 43;
#endif

DO_EXPORT int func() {
    return retval;
}
