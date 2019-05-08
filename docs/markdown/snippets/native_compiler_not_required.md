## Native (build machine) compilers not always required

`add_languages()` gained a `native:` keyword, indicating if a native or cross
compiler is to be used. Currently, for backwards compatibility, if the keyword
is absent, that means both are used.
