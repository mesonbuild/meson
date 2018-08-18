#include "subdir/exports.h"

int shlibfunc();

int DLL_PUBLIC statlibfunc() {
    return shlibfunc();
}
