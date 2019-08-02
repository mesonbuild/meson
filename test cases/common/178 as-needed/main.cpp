#include <cstdlib>

#include "libA.h"

int main() {
  return !meson_test_as_needed::linked ? EXIT_SUCCESS : EXIT_FAILURE;
}
