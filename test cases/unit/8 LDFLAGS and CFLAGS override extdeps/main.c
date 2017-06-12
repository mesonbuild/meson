#include <stdio.h>
#include <string.h>

#include "zlib.h"

int main (int argc, char *argv[])
{
  int ret = 0;
  const char *v = zlibVersion ();

  if (ZLIB_VER_MAJOR != 9999) {
    fprintf (stderr, "Compiled against the wrong zlib\n");
    ret = -1;
  }

  if (strcmp (v, "fake") != 0) {
    fprintf (stderr, "Value is %s instead of 'fake'\n", v);
    ret = -1;
  }
  return ret;
}
