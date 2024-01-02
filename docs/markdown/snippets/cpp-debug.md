## `ndebug` setting now controls C++ stdlib assertions

The `ndebug` setting, if disabled, now passes preprocessor defines to enable
debugging assertions within the C++ standard library.

For GCC, `-D_GLIBCXX_ASSERTIONS=1` is set.

For Clang, `-D_GLIBCXX_ASSERTIONS=1` is set to cover libstdc++ usage,
and `-D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_EXTENSIVE` or
`-D_LIBCPP_ENABLE_ASSERTIONS=1` is used depending on the Clang version.
