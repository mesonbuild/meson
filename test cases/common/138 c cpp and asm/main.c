#include <stdio.h>

int get_retval(void);

int main(int argc, char **argv) {
  printf("C seems to be working.\n");
  return get_retval();
}
