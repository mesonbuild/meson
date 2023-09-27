## New file_argument() function

Sometimes arguments need to be passed as a single string, but that string needs
to contain a File as part of the string. Consider how linker scripts work with GCC:
`-Wl,--version-script,<file>`. This is painful to deal with when the `<file>` is
a `files()` object. with `file_argument()` this becomes easier.

```meson
build_target(
  ...,
  c_args : [file_argument('--file-arg=', files('foo.file'))],
  link_args : [file_argument('-Wl,--version-script,', file('file.map'))],
)
```

Meson will automatically create the correct strings, relative to the build
directory, and will automatically add the file to the correct depends, so that
compilation and/or linking will correctly depend on that file.
