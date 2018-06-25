#if defined _WIN32 || defined __CYGWIN__
  #define DLL_IMPORT __declspec(dllimport)
#else
  #define DLL_IMPORT
#endif

// this is defined in the registry library
extern bool DLL_IMPORT plugin_was_loaded;

struct plugin_registrator_t {
    plugin_registrator_t() {
      plugin_was_loaded = true; // this will run on library initialization, when it is loaded
    }
} reg;