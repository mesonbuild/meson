#include<stdio.h>

int func();

int main(int argc, char **argv) {
    if(func() == 1) {
        printf("Iz success.\n");
    } else {
        printf("Iz fail.\n");
        return 1;
    }
    return 0;
}
