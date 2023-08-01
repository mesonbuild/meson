#include <string.h>
#include <stdio.h>
#include <stdlib.h>

int foo2(void);
int foo_process(void);

int main(int argc, char *argv[]) {
    if (argc >= 2) {
        const char *path = getenv("PATH");
        if (strstr(path, argv[1]) != 0) {
            printf("Not expecting exe directory in PATH\n");
            return 1;
        }
    }

    return foo_process() + foo2() == 4 ? 0 : 1;
}
