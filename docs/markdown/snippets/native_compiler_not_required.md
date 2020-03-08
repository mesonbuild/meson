## Native (build machine) compilers not always required

`add_languages()` gained a `native:` keyword, indicating if a native or cross
compiler is to be used.

For the benefit of existing simple build definitions which don't contain any
`native: true` targets, without breaking backwards compatibility for build
definitions which assume that the native compiler is available after
`add_languages()`, if the `native:` keyword is absent the languages may be used
for either the build or host machine, but are never required for the build
machine.

This changes the behaviour of the following meson fragment (when cross-compiling
but a native compiler is not available) from reporting an error at
`add_language` to reporting an error at `executable`.

```
add_language('c')
executable('main', 'main.c', native: true)
```
