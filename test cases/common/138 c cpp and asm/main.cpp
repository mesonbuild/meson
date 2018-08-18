#include <iostream>

extern "C" {
  int get_retval(void);
  int get_cval(void);
}

int main(int argc, char **argv) {
  std::cout << "C++ seems to be working." << std::endl;
  return get_retval();
}
