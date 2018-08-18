#include<stdio.h>

int main(int argc, char **argv) {
    if(argc != 2) {
        printf("I can not haz argument.\n");
        return 1;
    } else {
        printf("I can haz argument: %s\n", argv[1]);
    }
    return 0;
}
