/* Print the values of environment variables _compiler and _std. */

#include <stdio.h>
#include <stdlib.h>

int main(int argc,char **argv) {
    if (getenv("_compiler") == NULL || getenv("_std") == NULL) {
        printf("ERROR   : Test failed\n");
        exit(1);
    } else {
#if defined(__STDC_VERSION__)
        printf("NOTICE  : Test using %s -std=%s passed, __STDC_VERSION__=%ldL\n",
            getenv("_compiler"), getenv("_std"), __STDC_VERSION__);
#else
        printf("NOTICE  : Test using %s -std=%s passed, standard=%s\n",
            getenv("_compiler"), getenv("_std"), "ANSI-X3.159-1989");
#endif
        exit(0);
    }
}
