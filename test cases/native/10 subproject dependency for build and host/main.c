#include <gadget.h>
#include <stdio.h>

int
main (int argc,
      char * argv[])
{
  printf ("Gadget limit: %d\n", gadget_get_limit ());
  return 0;
}
