@visibility_macro@

#ifndef FOO_API_EXPORT
#error "FOO_API_EXPORT should be defined"
#endif
#ifndef FOO_API_IMPORT
#error "FOO_API_IMPORT should be defined"
#endif
#ifndef FOO_API
#error "FOO_API should be defined"
#endif

int main(void) {
    return 0;
}
