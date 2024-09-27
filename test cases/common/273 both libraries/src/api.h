#pragma once

#if defined EXPORT
    #if defined _WIN32 || defined __CYGWIN__
        #define API __declspec(dllexport)
    #else
        #if defined __GNUC__
            #define API __attribute__((visibility("default")))
        #else
            #define API
        #endif
    #endif
#else
    #define API
#endif
