#include "prog.orc.h"

int main(void)
{
  float src[10];
  float dst[10];
  int i;

  for (i = 0; i < 10; i++)
    src[i] = i;

  orc_sqrt(dst, src, 10); 
  return 0;
}
