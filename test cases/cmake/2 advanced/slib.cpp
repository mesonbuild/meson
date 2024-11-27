#include <iostream>
#include <cmMod.hpp>
#include "config.h"

#if CONFIG_OPT != 42
#error "Invalid value of CONFIG_OPT"
#endif

using namespace std;

void slib(void) {
  cmModClass obj("Hello from lib");
  cout << obj.getStr() << endl;
}
