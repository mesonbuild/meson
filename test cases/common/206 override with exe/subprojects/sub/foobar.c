#include <assert.h>
#include <stdio.h>

int main(int argc, char* argv[]) {
  FILE *f = fopen(argv[1], "w");
  const char msg[] = "foobar\n";
  size_t w = fwrite(msg, 1, sizeof(msg), f);
  assert(w == sizeof(msg));
  int r = fclose(f);
  assert(r == 0);
  return 0;
}
