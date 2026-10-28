#include <stdio.h>

int main(int argc, char *argv[]) {
  FILE *f;

  if (argc < 2)
    return 1;
  f = fopen(argv[1], "w");
  if (!f)
    return 1;
  fputs("int generated(void) { return 42; }\n", f);
  return fclose(f) != 0;
}
