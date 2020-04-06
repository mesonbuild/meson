#include "libfoo.h"

int func();

int call_foo()
{
  return func() == 1 ? 42 : 0;
}
