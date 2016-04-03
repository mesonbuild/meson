/* With MSVC, the DLL created from this will not export any symbols
 * without a module definitions file specified while linking */
#ifdef _MSC_VER
int somedllfunc() {
    return 42;
}
#endif
