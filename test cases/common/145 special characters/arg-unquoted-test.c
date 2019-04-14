#include <assert.h>
#include <string.h>

#define Q(x) #x
#define QUOTE(x) Q(x)

int main(int argc, char **argv) {
  const char *s = QUOTE(CHAR);
  assert(strlen(s) == 1);
  assert(s[0] == argv[1][0]);
  // There is no way to convert a macro argument into a character constant.
  // Otherwise we'd test that as well
}
