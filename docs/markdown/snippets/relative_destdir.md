## Install DESTDIR relative to build directory

When `DESTDIR` environment or `meson install --destdir` option is a relative path,
it is now assumed to be relative to the build directory. An absolute path will be
set into environment when executing scripts. It was undefined behavior in prior
Meson versions but was working as relative to build directory most of the time.
