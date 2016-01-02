#include<string.h>
#include<stdio.h>

int main(int argc, char **argv) {
    if(strcmp(DEF_WITH_BACKSLASH, "foo\\bar")) {
        printf("Arg string is quoted incorrectly: %s\n", DEF_WITH_BACKSLASH);
        return 1;
    }
    return 0;
}
