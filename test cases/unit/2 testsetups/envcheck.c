#include <stdlib.h>

int
main(void)
{
    if (getenv("PATH") == NULL)
        return 1;

    return 0;
}
