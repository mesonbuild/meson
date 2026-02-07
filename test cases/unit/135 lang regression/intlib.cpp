#include <cstdio>

#if defined _WIN32

extern "C" int __declspec(dllimport) pcre2_function();

#else

extern "C" int pcre2_function();

#endif

int internal_function() {
    return pcre2_function();
}
