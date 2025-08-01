#pragma once

// let's just assume the default isn't c18.
#if __STDC_VERSION__ == 201710L
typedef struct Datatype {
    int x;
} Datatype;
#else
#error C standard version not set!
#endif
