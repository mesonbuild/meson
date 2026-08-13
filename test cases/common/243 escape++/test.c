#include <stdio.h>

int main(int argc, char **argv) {
    if(argc > 1) {
        printf("A command line argument was passed to this program.\n");
        (void)argv;
    }
    return 0;
}
