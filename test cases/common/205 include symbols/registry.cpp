#include "dll_macros.h"

// the plugin library sets this to "true" when it is loaded
bool DLL_PUBLIC plugin_was_loaded = false;

bool DLL_PUBLIC was_plugin_loaded() {
  return plugin_was_loaded;
}
