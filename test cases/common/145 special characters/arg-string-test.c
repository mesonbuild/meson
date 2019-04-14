#include <assert.h>
#include <string.h>

int main(int argc, char **argv) {
  const char *s = CHAR;
  assert(strlen(s) == 1);
  assert(s[0] == argv[1][0]);
}
