## `stldebug` gains Clang support

For Clang, we now pass `-D_GLIBCXX_DEBUG=1` if `debugstl` is enabled, and
we also pass `-D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_DEBUG`.
