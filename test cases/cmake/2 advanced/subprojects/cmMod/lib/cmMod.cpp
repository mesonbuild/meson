#include "cmMod.hpp"
#include <zlib.h>

using namespace std;

cmModClass::cmModClass(string foo) {
  str = foo + " World " + zlibVersion();
}

string cmModClass::getStr() const {
  return str;
}
