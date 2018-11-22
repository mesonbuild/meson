## CMake `find_package` dependency backend

Meson can now use the CMake `find_package` ecosystem to
detect dependencies. Both the old-style `<NAME>_LIBRARIES`
variables as well as imported targets are supported. Meson
can automatically guess the correct CMake target in most
cases but it is also possible to manually specify a target
with the `modules` property.

```meson
# Implicitly uses CMake as a fallback and guesses a target
dep1 = dependency('KF5TextEditor')

# Manually specify one or more CMake targets to use
dep2 = dependency('ZLIB', method : 'cmake', modules : ['ZLIB::ZLIB'])
```

CMake is automatically used after `pkg-config` fails when
no `method` (or `auto`) was provided in the dependency options.
