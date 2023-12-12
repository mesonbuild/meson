#include "library.h"

int library_function(void)
{
#if defined EXPORT
    return 1;
#else
    return 0;
#endif
}
