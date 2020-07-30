## Custom standard library

- It is not limited to cross builds any more, `<lang>_stdlib` property can be
  set in native files.
- The variable name parameter is no longer required as long as the subproject
  calls `meson.override_dependency('c_stdlib', mylibc_dep)`.
