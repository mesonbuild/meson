#include<stdint.h>

int is_big_endian(void) {
    union {
        uint32_t i;
        char c[4];
    } bint = {0x01020304};

    return bint.c[0] == 1;
}


int main(int argc, char **argv) {
    int is_be_check = is_big_endian();
    int is_be;
#ifdef IS_BE
    is_be = 1;
#else
    is_be = 0;
#endif
    if(is_be_check && is_be)
        return 0;
    if(!is_be_check && !is_be)
        return 0;
    return 1;
}
