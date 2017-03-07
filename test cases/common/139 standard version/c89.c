int main()
{
    /* __STDC_VERSION__ should be 199409L in C89, but it may not be defined at all. */
    #ifdef __STDC_VERSION
    return __STDC_VERSION__ ==  199409L ? 0 : 1;
    #else
    return 0;
    #endif
}
