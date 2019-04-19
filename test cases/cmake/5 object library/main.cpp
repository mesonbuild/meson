#include <iostream>
#include "libA.hpp"
#include "libB.hpp"

using namespace std;

int main() {
  cout << getLibStr() << " -- " << getZlibVers() << endl;
}
