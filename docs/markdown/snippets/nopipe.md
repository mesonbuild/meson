## `-pipe` no longer used by default

Meson used to add the `-pipe` command line argument to all compilers
that supported it, but no longer does. If you need this, then you can
add it manually. However note that you should not do this unless you
have actually measured that it provides performance improvements. In
our tests we could not find a case where adding `-pipe` made
compilation faster and using `-pipe` [can cause sporadic build
failures in certain
cases](https://github.com/mesonbuild/meson/issues/8508).
