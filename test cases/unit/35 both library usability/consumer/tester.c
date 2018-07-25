#include <stdio.h>

#if defined(_MSC_VER) && !defined(PROVIDER_STATIC)
__declspec(dllimport)
#endif
int both_get_dat_value (void);

int main (int argc, char *argv[])
{
  int got = both_get_dat_value ();

  if (got != 111) {
    printf ("Got %i instead of 111\n", got);
    return 2;
  }
  return 0;
}
