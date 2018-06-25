#if defined _WIN32 || defined __CYGWIN__
  #define DLL_IMPORT __declspec(dllimport)
#else
  #define DLL_IMPORT
#endif

// this is defined in the "middle" library
bool DLL_IMPORT was_plugin_loaded();

int main() {
    return was_plugin_loaded() ? 0 : 1;
}
