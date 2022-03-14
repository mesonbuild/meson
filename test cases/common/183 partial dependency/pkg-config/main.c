#include "system.h"

#ifdef FAIL
#  error("Got unexpected cflags");
#endif

int main(void) {
    return foo();
}
