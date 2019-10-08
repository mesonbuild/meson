#include <iostream>
#include <fstream>

using namespace std;

int main(int argc, const char *argv[]) {
  if(argc != 3 || string(argv[1]) != "arg1" || string(argv[2]) != "arg2") {
    cerr << argv[0] << " requires 2 args" << endl;
    return 1;
  }

  ofstream out1("cmModLib.hpp");
  out1 << "#define FOO = \"plop\"";


  return 0;
}
