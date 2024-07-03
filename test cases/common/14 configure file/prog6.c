#include <string.h>
#include <config6.h>

int main(void) {
    return strcmp(MESSAGE1, "foo")
        || strcmp(MESSAGE2, "@var1@")
        || strcmp(MESSAGE3, "\\@var1@")
        || strcmp(MESSAGE4, "\\@var1@")
        || strcmp(MESSAGE5, "\\@var1")
        || strcmp(MESSAGE6, "\\ @ \\@")
        || strcmp(MESSAGE7, "@var1")
        || strcmp(MESSAGE8, "\\@var1bar")
        || strcmp(MESSAGE9, "foovar2@")
        || strcmp(MESSAGE10, "foovar2\\@")
        || strcmp(MESSAGE11, "foobarbazqux")
        || strcmp(MESSAGE12, "foovar2\\@var3@var4\\@");
}
