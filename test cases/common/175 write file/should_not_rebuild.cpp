#include <iostream>

#include "test_writefile.h"

#warning The file was rebuilt !!

void function_no_rebuild() {
  std::cout << "Hello world!" << std::endl;
  std::cout << "Test value: " << test_value << std::endl;
}


int main(int argc, char const *argv[]) {
  function_no_rebuild();
  return 0;
}
