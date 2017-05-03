int main()
{
    #ifdef _MSC_VER
    // Visual studio always returns 199711, so disable this test.
    // https://connect.microsoft.com/VisualStudio/feedback/details/763051/a-value-of-predefined-macro-cplusplus-is-still-199711l
    return 0;
    #else
    return __cplusplus == 201103 ? 0 : 1;
    #endif
}
