#include <iostream>
#include "lib/cmMod.hpp"

using namespace std;

int main() {
  cmModClass obj("Hello (LIB TEST)");
  cout << obj.getStr() << endl;
  return 0;
}
