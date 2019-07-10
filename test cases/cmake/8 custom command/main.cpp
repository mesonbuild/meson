#include <iostream>
#include <cmMod.hpp>

using namespace std;

int main() {
  cmModClass obj("Hello");
  cout << obj.getStr() << endl;
  cout << obj.getOther() << endl;
  return 0;
}
