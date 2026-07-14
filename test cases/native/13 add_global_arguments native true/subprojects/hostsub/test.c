#include "stdio.h"

#ifdef USING_LOCAL_STDIO
#error unexpected argument for native: true
#endif

int main(void) {}
