#if defined(_MSC_VER) && !defined(PROVIDER_STATIC)
__declspec(dllexport)
#endif
int get_dat_value (void)
{
  return 69;
}
