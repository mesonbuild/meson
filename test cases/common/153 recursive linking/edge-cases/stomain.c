#include <stdio.h>

#include "../lib.h"

int get_stodep_value (void);

int main(int argc, char *argv[]) {
  int val;

  val = get_stodep_value ();
  if (val != 1) {
    printf("st1 value was %i instead of 1\n", val);
    return -1;
  }
  return 0;
}
