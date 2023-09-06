## Support for `Requires.internal` in `pkg.generate()`

If `internal: true` argument is given, `Requires.internal` field will
be used for dependencies instead of `Requires.private`. This create better pc files,
but only supported by `pkgconf` and not the original `pkg-config` implementation.
There are 3 types of dependencies: public, private and internal.
- public: To use libfoo an app also need to use symbols from libbar. An app that
  uses libfoo must also link to libbar.
- private: To use libfoo an app don't generally use symbols from libbar, but headers
  from libfoo still include headers from libbar, for example for type definitions.
  An app that uses libfoo does not link to libbar, but libbar is still a build-dep
  of the app.
- internal: libfoo uses libbar but does not expose any of its API. An app that
  uses libfoo only need libbar for static linking, libbar is not a build-dep
  unless the static libfoo library is used.
As a result, pkg-config will output cflags from `Requires.private` even without
`--static`, but not cflags from `Requires.internal`.
