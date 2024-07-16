#include <zlib.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

static bool check_version(const char *zlib_ver, const char *found_zlib) {
    if (zlib_ver == found_zlib)
        return true;

    if (strcmp(zlib_ver, found_zlib) == 0)
        return true;

#ifdef ZLIBNG_VERSION
    const char *ptr = strstr(zlib_ver, found_zlib);

    // If the needle isn't found or the needle isn't at the start, fail.
    if (ptr == NULL || ptr != zlib_ver)
        return false;

    /* In zlib-ng, ZLIB_VERSION is of the form X.Y.Z.zlib-ng. This will move the
     * pointer to the start of the suffix, .zlib-ng. We know that at this point
     * that FOUND_ZLIB is the start of ZLIB_VERSION, so compare the rest.
     */
    ptr += strlen(found_zlib);
    if (strcmp(ptr, ".zlib-ng") == 0)
        return true;
#endif

    return false;
}

int main(void) {
    void * something = deflate;
    if (!check_version(ZLIB_VERSION, FOUND_ZLIB)) {
        printf("Meson found '%s' but zlib is '%s'\n", FOUND_ZLIB, ZLIB_VERSION);
#ifdef ZLIBNG_VERSION
        puts("Note that in the case of zlib-ng, a version suffix of .zlib-ng is expected");
#endif
        return 2;
    }
    if(something != 0)
        return 0;
    printf("Couldn't find 'deflate'\n");
    return 1;
}
