#if defined _WIN32 || defined __CYGWIN__
  #define DLL_IMPORT __declspec(dllimport)
#else
  #define DLL_IMPORT
#endif

int DLL_IMPORT func_sym(void);
int DLL_IMPORT func(void);

int main(void) {
    return func_sym();
}
