#include "both_libraries.h"

int both_libraries_function(void)
{
#if defined EXPORT
    return 1;
#else
    return 0;
#endif
}
