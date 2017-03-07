int main()
{
    #ifdef _MSC_VER
    /* Visual studio does not support C standard versions, so
       fake success for this test. */
    return 0;
    #else
    return __STDC_VERSION__ ==  199901L ? 0 : 1;
    #endif
}
