#include<stdlib.h>

#ifdef _WIN32

int __declspec(dllexport) pcre2_function(void);

#else

int pcre2_function(void);

#endif

int pcre2_function(void) {
    return 0;
}
