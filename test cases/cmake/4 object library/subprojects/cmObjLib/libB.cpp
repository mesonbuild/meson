#include "libB.hpp"
#include <zlib.h>

std::string getZlibVers() {
  return zlibVersion();
}
