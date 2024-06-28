#include "cmMod_internal.hpp"

using namespace std;

cmModInternalClass::cmModInternalClass(const std::string &foo) {
  str = "Inner " + foo;
}

string cmModInternalClass::getStr() const {
  return str;
}
