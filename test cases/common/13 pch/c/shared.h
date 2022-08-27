#pragma once

#include <math.h>

#if defined _WIN32 || defined __CYGWIN__
#if defined BUILDING_DLL
  #define DLL_PUBLIC __declspec(dllexport)
#else
  #define DLL_PUBLIC __declspec(dllimport)
#endif
#else
  #if defined __GNUC__
    #define DLL_PUBLIC __attribute__ ((visibility("default")))
  #else
    #pragma message ("Compiler does not support symbol visibility.")
    #define DLL_PUBLIC
  #endif
#endif

extern long DLL_PUBLIC shared_lrint(double);
