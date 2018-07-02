#include "dll_macros.h"

// this is defined in the registry library
bool DLL_IMPORT was_plugin_loaded();

int main() {
  // returning "success" if the plugin library was loaded
  return was_plugin_loaded() ? 0 : 1;
}
