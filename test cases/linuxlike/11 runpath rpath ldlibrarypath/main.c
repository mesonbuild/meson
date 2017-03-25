#include <stdio.h>

int some_symbol (void);

int main (int argc, char *argv[]) {
  int ret = some_symbol ();
  if (ret == 1)
    return 0;
  fprintf (stderr, "ret was %i instead of 1\n", ret);
  return -1;
}
