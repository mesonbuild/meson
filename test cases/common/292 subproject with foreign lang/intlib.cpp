#include <cstdio>

#if defined _WIN32

extern "C" int __declspec(dllimport) pcre2_function(void);

#else

extern "C" int pcre2_function(void);

#endif

int internal_function(void) {
    return pcre2_function();
}
