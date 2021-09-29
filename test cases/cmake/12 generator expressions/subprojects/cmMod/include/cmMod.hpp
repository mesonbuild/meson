#pragma once

#include <string>

#ifndef CMAKE_FLAG_REQUIRED_A
#error "The flag CMAKE_FLAG_REQUIRED_A was not set"
#endif

#ifndef CMAKE_FLAG_REQUIRED_B
#error "The flag CMAKE_FLAG_REQUIRED_B was not set"
#endif

#ifndef CMAKE_FLAG_REQUIRED_C
#error "The flag CMAKE_FLAG_REQUIRED_C was not set"
#endif

#ifdef CMAKE_FLAG_ERROR_A
#error "The flag CMAKE_FLAG_ERROR_A was set"
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
