#include <stdlib.h>
#include <clib.h>

int main(void) {
    if (clib_fun () == 42)
        return EXIT_SUCCESS;
    else
        return EXIT_FAILURE;
}
