== Link tests can use sources for a different compiler ==

Usually, the `links` method of the compiler object uses a single program
invocation to do both compilation and linking.  Starting with this version,
whenever the argument to `links` is a file, Meson will check if the file
suffix matches the compiler object's language.  If they do not match,
as in the following case:

```
cxx = meson.get_compiler('cpp')
cxx.links(files('test.c'))
```

then Meson will separate compilation and linking.  In the above example
`test.c` will be compiled with a C compiler and the resulting object file
will be linked with a C++ compiler.  This makes it possible to detect
misconfigurations of the compilation environment, for example when the
C++ runtime is not compatible with the one expected by the C compiler.

For this reason, passing file arguments with an unrecognized suffix to
`links` will cause a warning.
