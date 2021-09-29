#include "cmMod.hpp"
#include "genTest.hpp"
#include "cpyBase.hpp"
#include "cpyNext.hpp"
#include "cpyTest.hpp"
#include "cmModLib.hpp"

#ifndef FOO
#error FOO not declared
#endif

using namespace std;

cmModClass::cmModClass(string foo) {
  str = foo + " World";
}

string cmModClass::getStr() const {
  return str;
}

string cmModClass::getOther() const {
  return "Srings:\n - " + getStrCpy() + "\n - " + getStrNext() + "\n - " + getStrCpyTest();
}
