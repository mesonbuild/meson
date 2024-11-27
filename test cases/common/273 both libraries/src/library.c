#include "library.h"
#include "both_libraries.h"

int library_function(void)
{
    int sum = both_libraries_function();
#if defined EXPORT
    return sum + 1;
#else
    return sum;
#endif
}
