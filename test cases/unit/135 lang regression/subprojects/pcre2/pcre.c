#include<stdlib.h>

#ifdef _WIN32

int __declspec(dllexport) pcre2_function();

#endif

int pcre2_function() {
    return 0;
}
