#include <assert.h>

int main(int argc, char **argv) {
  char c = CHAR;
  assert(c == argv[1][0]);
}
