#include<stdio.h>

int func(); /* Files in different subdirs return different values. */

int main(int argc, char **argv) {
    if(func() == 0) {
        printf("Iz success.\n");
    } else {
        printf("Iz fail.\n");
        return 1;
    }
    return 0;
}
