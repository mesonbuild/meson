#if defined(_MSC_VER) && !defined(PROVIDER_STATIC)
__declspec(dllimport)
#endif
int get_dat_value (void);

#ifdef INSTALLED_LIBRARY
  #define EXPECTED_VALUE 69
#else
  #define EXPECTED_VALUE 42
#endif

#if defined(_MSC_VER) && !defined(PROVIDER_STATIC)
__declspec(dllexport)
#endif
int both_get_dat_value (void)
{
  if (get_dat_value () != EXPECTED_VALUE)
    return 666;
  return 111;
}
