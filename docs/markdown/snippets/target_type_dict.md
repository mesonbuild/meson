## Dictionary for `name_prefix`, `name_suffix` and `<lang>_args`

`name_prefix`, `name_suffix` and `<lang>_args` keyword arguments of functions
like `library()` and `build_target()` now accept a dictionary mapping the target
type to the value. This is used when for example different c_args must be passed
to the static and shared library built by `both_libraries()`.

```meson
cargs = {
  'static_library': '-DSTATIC',
  'shared_library': '-DSHARED',
  'executable': ['-DEXECUTABLE', '-DMY_APP'],
 }
namesuffix = {
  'static_library': 'a',
  'shared_library': 'so',
}
# sources will be built twice with different cflags, the static library will
# have .a extension on all platforms and the shared library will have the .so
# extension on all platforms
both_libraries('foo', sources, c_args: cargs, name_suffix: namesuffix)
# EXECUTABLE and MY_APP will be defined when building sources, and it will use
# the default extension on the current platform because 'executable' is not in
# the namesuffix dictionary
executable('app', c_args: cargs, name_suffix: namesuffix)
```
