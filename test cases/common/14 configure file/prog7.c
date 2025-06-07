#include <string.h>
#include <config7.h>

int main(void) {
    return strcmp(MESSAGE1, "foo")
        || strcmp(MESSAGE2, "\foo")
        || strcmp(MESSAGE3, "\\\\foo")
        || strcmp(MESSAGE4, "\\\\\foo")
        || strcmp(MESSAGE5, "foo")
        || strcmp(MESSAGE6, "\\foo")
        || strcmp(MESSAGE7, "\\\\foo")
        || strcmp(MESSAGE8, "@var1\@")
        || 0;
}
