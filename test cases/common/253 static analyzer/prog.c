#include <stdio.h>
#include <stdlib.h>

int main(void) {
    char *ptr;

    ptr = malloc(10 * sizeof(char));
    if (!ptr) {
        printf("Error allocating memory.\n");
        return -1;
    }

    free(ptr);
    return 0;
}
