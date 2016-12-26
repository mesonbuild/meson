#include<stdio.h>
#include<stdlib.h>

#include<impl.h>

int main(int argc, char **argv) {
    char *ten = malloc(10);
    do_nasty(ten);
    free(ten);
    return 0;
}
