#include "dll_macros.h"

// this is defined in the registry library
extern bool DLL_IMPORT plugin_was_loaded;

struct plugin_registrator_t {
  plugin_registrator_t() {
    plugin_was_loaded = true; // this will run when the library is loaded
  }
} reg;

extern "C" { // to avoid C++ name mangling
  // this is used just to grab the library with it
  void DLL_PUBLIC plugin_dummy() { }
}
