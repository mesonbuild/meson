#include "subdir/exports.h"

int statlibfunc(void);

int DLL_PUBLIC shlibfunc2(void) {
    return statlibfunc() - 18;
}
