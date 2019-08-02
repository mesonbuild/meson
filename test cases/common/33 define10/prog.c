#include<stdio.h>
#include"config.h"

int main(int argc, char **argv) {
    if(ONE != 1) {
        fprintf(stderr, "ONE is not 1.\n");
        return 1;
    }
    if(ZERO != 0) {
        fprintf(stderr, "ZERO is not 0.\n");
    }
    return 0;
}
