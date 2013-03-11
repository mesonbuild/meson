#include <string.h>
#include "config.h"

#ifdef SHOULD_BE_UNDEF
#error "FAIL!"
#endif

int main(int argc, char **argv) {
#ifndef BE_TRUE
    return 1;
#else
    return strcmp(MESSAGE, "mystring");
#endif
}
