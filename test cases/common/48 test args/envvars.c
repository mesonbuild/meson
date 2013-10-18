#include<stdio.h>
#include<string.h>
#include<stdlib.h>

int main(int argc, char **argv) {
    if(strcmp(getenv("first"), "val1") != 0) {
        fprintf(stderr, "First envvar is wrong.\n");
        return 1;
    }
    if(strcmp(getenv("second"), "val2") != 0) {
        fprintf(stderr, "Second envvar is wrong.\n");
        return 1;
    }
    return 0;
}
