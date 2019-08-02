#include "mylib.h"

DO_IMPORT int func();
DO_IMPORT int retval;

int main(int argc, char **arg) {
    return func() == retval ? 0 : 1;
}
