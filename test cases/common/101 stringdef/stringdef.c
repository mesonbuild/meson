#include<stdio.h>
#include<string.h>

int main(int argc, char **argv) {
    if(strcmp(FOO, "bar")) {
        printf("FOO is misquoted: %s\n", FOO);
        return 1;
    }
    return 0;
}
