#if defined SHAR
int func() {
    return 1;
}
#elif defined STAT
int func() {
    return 0;
}
#else
#error "Missing type definition."
#endif

