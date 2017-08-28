#include <cups/cups.h>

int
main()
{
    return !cupsGetDefault();
}
