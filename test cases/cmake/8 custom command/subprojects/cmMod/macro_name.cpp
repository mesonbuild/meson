#include <iostream>
#include <fstream>
#include <chrono>
#include <thread>

using namespace std;

int main() {
  this_thread::sleep_for(chrono::seconds(1));
  ofstream out1("macro_name.txt");
  out1 << "FOO";

  return 0;
}
