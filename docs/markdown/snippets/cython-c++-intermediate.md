## Cython can now transpile to C++ as an intermediate language

Built-in cython support currently only allows C as an intermediate language, now
C++ is also allowed. This can be set via the `cython_language` option, either on
the command line, or in the meson.build files.

```meson
project(
  'myproject',
  'cython',
  default_options : ['cython_language=cpp'],
)
```

or on a per target basis with:
```meson
python.extension_module(
  'mod',
  'mod.pyx',
  override_options : ['cython_language=cpp'],
)
```
