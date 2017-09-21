#include <stdio.h>
#include <string.h>  // for strlen
#include <assert.h>
#include "zlib.h"

// Inspired from: http://stackoverflow.com/questions/7540259/deflate-and-inflate-zlib-h-in-c
int main(int argc, char* argv[])
{
    // original string len = 36
    char a[50] = "Hello Hello Hello Hello Hello Hello!";
    char b[50];

    // deflate a into b. (that is, compress a into b)
    // zlib struct
    z_stream defstream;
    defstream.zalloc = Z_NULL;
    defstream.zfree = Z_NULL;
    defstream.opaque = Z_NULL;
    // setup "a" as the input and "b" as the compressed output
    defstream.avail_in = (uInt)strlen(a)+1; // size of input, string + terminator
    defstream.next_in = (Bytef *)a; // input char array
    defstream.avail_out = (uInt)sizeof(b); // size of output
    defstream.next_out = (Bytef *)b; // output char array

    // the actual compression work.
    deflateInit(&defstream, Z_BEST_COMPRESSION);
    deflate(&defstream, Z_FINISH);
    deflateEnd(&defstream);

    return 0;
}
