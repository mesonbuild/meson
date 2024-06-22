## New version_argument kwarg for find_program

When finding an external program with `find_program`, the `version_argument`
can be used to override the default `--version` argument when trying to parse
the version of the program.

For example, if the following is used:
```meson
foo = find_program('foo', version_argument: '-version')
```

meson will internally run `foo -version` when trying to find the version of `foo`.
