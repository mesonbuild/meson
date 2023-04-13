## Support for defining crate names of Rust dependencies in Rust targets

Rust supports defining a different crate name for a dependency than what the
actual crate name during compilation of that dependency was.

This allows using multiple versions of the same crate at once, or simply using
a shorter name of the crate for convenience.

```meson
a_dep = dependency('some-very-long-name')

my_executable = executable('my-executable', 'src/main.rs',
  rust_dependency_map : {
    'some_very_long_name' : 'a',
  },
  dependencies : [a_dep],
)
```
