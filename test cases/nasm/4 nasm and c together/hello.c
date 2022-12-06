#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

extern uint32_t dummy[]; 

int main()
{
    if (*dummy != 0x00010203u) {
        fprintf(stderr, "Dummy value was: %" PRIu32 "\n", *dummy);
        return 1;
    }

    return 0;
}
