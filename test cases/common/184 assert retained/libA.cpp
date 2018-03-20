#define BUILDING_DLL

#include "libA.h"

namespace meson_test_assert_retained {
  DLL_PUBLIC bool changed = false;

  DLL_PUBLIC bool libA_func() {
    changed = true;
    return changed;
  }
}
