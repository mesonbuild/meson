#include<simdfuncs.h>
#include<stdio.h>

/*
 * A function that checks at runtime if simd acceleration is
 * available and calls the respective function if it is. Falls
 * back to plain C implementation if not.
 */

int main(int argc, char **argv) {
    float four[4] = {2.0, 3.0, 4.0, 5.0};
    const float expected[4] = {3.0, 4.0, 5.0, 6.0};
    void (*fptr)(float[4]) = NULL;

#if HAVE_MMX
    if(mmx_available()) {
        fptr = increment_mmx;
    }
#endif
    if(fptr == NULL) {
        fptr = increment_fallback;
    }
    fptr(four);
    for(int i=0; i<4; i++) {
        if(four[i] != expected[i]) {
            printf("Increment function failed.\n");
            return 1;
        }
    }
    return 0;
}
