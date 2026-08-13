#include<stdio.h>

int main(int argc, char **argv) {
    /* Have a non-elidable branch to make sure coverage info is not empty. */
    if(argc > 1) {
        printf("A command line argument was passed to the program.\n");
        (void)argv;
    }
    printf("Trivial test is working.\n");
    return 0;
}
