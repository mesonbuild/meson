#include "cmMod.hpp"
#include "cmMod_internal.hpp"

using namespace std;

cmModClass::cmModClass(const std::string &foo) {
  str = "Outer " + cmModInternalClass{foo}.getStr();
}

string cmModClass::getStr() const {
  return str;
}
