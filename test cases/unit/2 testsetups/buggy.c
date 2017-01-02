#include<stdio.h>
#include<stdlib.h>

#include<impl.h>

int main(int argc, char **argv) {
    char *ten = malloc(10);
    do_nasty(ten);
    free(ten);
    if(getenv("TEST_ENV")) {
        printf("TEST_ENV is set.\n");
    }
    return 0;
}
