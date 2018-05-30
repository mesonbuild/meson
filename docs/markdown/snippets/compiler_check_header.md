## New compiler check: check_header()

The existing compiler check `has_header()` only checks if the header exists,
either with the `__has_include` C++11 builtin, or by running the pre-processor.

However, sometimes the header you are looking for is unusable on some platforms
or with some compilers in a way that is only detectable at compile-time. For
such cases, you should use `check_header()` which will include the header and
run a full compile.

Note that `has_header()` is much faster than `check_header()`, so it should be
used whenever possible.
