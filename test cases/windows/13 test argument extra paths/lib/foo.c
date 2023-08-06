#include "config.h"

int static_func(void);
DLL_PUBLIC int foo_process(void);

int
foo_process(void) {
  return static_func() + 1;
}
