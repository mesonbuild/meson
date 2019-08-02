#pragma once

#include <string>

#ifndef CMAKE_FLAG_MUST_BE_PRESENT
#error "The flag CMAKE_FLAG_MUST_BE_PRESENT was not set"
#endif

class cmModClass {
  private:
    std::string str;
  public:
    cmModClass(std::string foo) {
      str = foo + " World ";
      str += CMAKE_COMPILER_DEFINE_STR;
    }

    inline std::string getStr() const { return str; }
};
