#ifdef _WIN32
// FIXME: add implementation using Winapi functions for dlopen.

int main(int argc, char **argv) {
    return 0;
}

#else

#include<dlfcn.h>
#include<assert.h>
#include<stdio.h>

int func();
int func_from_language_runtime();

int main(int argc, char **argv) {
    void *dl;
    int (*importedfunc)();
    int success;
    char *error;

    dlerror();
    dl = dlopen(argv[1], RTLD_LAZY);
    error = dlerror();
    if(error) {
        printf("Could not open %s: %s\n", argv[1], error);
        return 1;
    }
    importedfunc = (int (*)()) dlsym(dl, "func");
    assert(importedfunc);
    assert(importedfunc != func_from_language_runtime);
    success = (*importedfunc)() == func_from_language_runtime();
    dlclose(dl);
    return !success;
}

#endif
