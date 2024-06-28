#include <iostream>

#include <cmMod.hpp>

using namespace std;

int main(void) {
  cmModClass obj("World");
  cout << obj.getStr() << endl;
  return 0;
}
