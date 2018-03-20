#include <cassert>
#include <cstdlib>

#include "libA.h"

int main() {
  assert(meson_test_assert_removed::libA_func());
  return (!meson_test_assert_removed::changed ? EXIT_SUCCESS : EXIT_FAILURE);
}
