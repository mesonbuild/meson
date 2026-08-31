#include "clib.h"
#include <libxml2/libxml/xmlversion.h>
#include <exampleshlib.h>
#include <stdio.h>

void clib_call_cdeps(void) {
    printf("clib_call_cdeps called.\n");
    exampleshlib_hello();
    LIBXML_TEST_VERSION
}
