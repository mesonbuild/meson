#include "cmMod.hpp"
#include "cmSys.hpp"

#ifndef CM_SYS_INCLUDED
#error cmSys.hpp not included
#endif

using namespace std;

cmModClass::cmModClass(string foo) {
  str = foo + " World";
}

string cmModClass::getStr() const {
  return str;
}
