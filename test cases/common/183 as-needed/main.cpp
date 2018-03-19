#include <cstdlib>

#include "libA.h"

int main() {
  return (meson_test_as_needed::linked == false ? EXIT_SUCCESS : EXIT_FAILURE);
}
