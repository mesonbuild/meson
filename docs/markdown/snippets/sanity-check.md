## Sanity checking compilers with user flags

Sanity checks previously only used user-specified flags for cross compilers, but
now do in all cases.

All compilers meson might decide to use for the build are "sanity checked"
before other tests are run. This usually involves building simple executable and
trying to run it. Previously user flags (compilation and/or linking flags) were
used for sanity checking cross compilers, but not native compilers.  This is
because such flags might be essential for a cross binary to succeed, but usually
aren't for a native compiler.

In recent releases, there has been an effort to minimize the special-casing of
cross or native builds so as to make building more predictable in less-tested
cases. Since this the user flags are necessary for cross, but not harmful for
native, it makes more sense to use them in all sanity checks than use them in no
sanity checks, so this is what we now do.
