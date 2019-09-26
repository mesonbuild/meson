#include <iostream>
#include <cmMod.hpp>

using namespace std;

int main() {
  cmModClass obj("Hello");
  cout << obj.getStr() << endl;
  return 0;
}
