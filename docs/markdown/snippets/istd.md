## Experimental C++ import std support

**Note**: this feature is experimental and not guaranteed to be
  backwards compatible or even exist at all in future Meson releases.

Meson now supports `import std`, a new, modular way of using the C++
standard library. This support is enabled with the new `cpp_importstd`
option. It defaults to `false`, but you can set it to `true` either
globally or per-target using `override_options` in the usual way.

The implementation has many limitations. The biggest one is that the
same module file is used on _all_ targets. That means you can not mix
multiple different C++ standards versions as the compiled module file
can only be used with the same compiler options as were used to build
it. This feature only works with the Ninja backend.

As `import std` is a major new feature in compilers, expect to
encounter toolchain issues when using it. For an example [see
here](https://gcc.gnu.org/bugzilla/show_bug.cgi?id=122614).
