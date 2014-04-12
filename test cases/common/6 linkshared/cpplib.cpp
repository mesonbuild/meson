#if defined _WIN32
    #define DLL_PUBLIC __declspec(dllexport)
#else
    #define DLL_PUBLIC __attribute__ ((visibility ("default")))
#endif

int DLL_PUBLIC cppfunc() {
    return 42;
}
