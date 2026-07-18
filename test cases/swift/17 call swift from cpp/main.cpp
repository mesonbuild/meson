#include "Library-Swift.h"
#include <stdio.h>

int main()
{
    if (std::string(Library::callMe("To Swift")) != "To Swift, and back") {
        fprintf(stderr, "got wrong return value\n");
        abort();
    }
}
