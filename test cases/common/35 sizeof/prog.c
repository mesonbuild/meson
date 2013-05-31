#include"config.h"
#include<stdio.h>

int main(int argc, char **argv) {
    if(INTSIZE != sizeof(int)) {
        fprintf(stderr, "Mismatch: detected int size %d, actual size %d.\n", INTSIZE, (int)sizeof(int));
        return 1;
    }
    return 0;
}
