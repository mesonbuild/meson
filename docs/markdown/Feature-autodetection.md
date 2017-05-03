---
short-description: Auto-detection of features like ccache and code coverage
...

# Feature autodetection

Meson is designed for high productivity. It tries to do as many things automatically as it possibly can.

CCache
--

[CCache](https://ccache.samba.org/) is a cache system designed to make compiling faster. When you run Meson for the first time for a given project, it checks if CCache is installed. If it is, Meson will use it automatically.

If you do not wish to use CCache for some reason, just specify your compiler with environment variables `CC` and/or `CXX` when first running Meson (remember that once specified the compiler can not be changed). Meson will then use the specified compiler without CCache.

Coverage
--

When doing a code coverage build, Meson will check the existence of binaries `gcovr`, `lcov` and `genhtml`. If the first one is found, it will create targets called *coverage-text* and *coverage-xml*. If the latter two are found, it generates the target *coverage-html*. You can then generate coverage reports just by calling e.g. `ninja coverage-xml`.
