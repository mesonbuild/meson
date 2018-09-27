#include <foo.h>
#include <string.h>

int
main (int argc, char * argv[])
{
    int foo_expected = 0;
    int bar_expected = 0;
    int i;

    for (i = 1; i < argc; i++) {
        if (strcmp (argv[i], "foo") == 0)
            foo_expected = 1;
        else if (strcmp (argv[i], "bar") == 0)
            bar_expected = 1;
        else
            return 1;
    }

    if (foo_is_static () != foo_expected ||
        bar_is_static () != bar_expected ||
        !shared_func())
        return 1;

    return 0;
}
