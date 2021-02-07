#include "cmMod.hpp"
#include "libPCTest.h"

using namespace std;

#if MESON_MAGIC_FLAG != 21
#error "Invalid MESON_MAGIC_FLAG (private)"
#endif

cmModClass::cmModClass(string foo) {
  str = foo + " World" + std::to_string(getOneInt());
}

string cmModClass::getStr() const {
  return str;
}
