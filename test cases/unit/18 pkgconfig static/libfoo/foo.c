int foo_is_static (void)
{
#ifdef STATIC_COMPILATION
    return 1;
#else
    return 0;
#endif
}
