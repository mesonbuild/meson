## Rust object crates

In order to link Rust objects into C/C++ libraries/programs without static
linking all crates/libraries used by the objects, the new 'object' type crate
can be used. It will produce object files instead of libraries from the Rust
sources. The caller is responsible for providing the linking parameters for
any crate/library needed by the Rust objects. Note that due to the instability
of Rustc, such object files might require extra work (e.g.: additional linking)
depending on the compiler version, and might change between versions. This
option is provided as-is, and it's the caller's responsibility to deal with
these issues.

```meson
libstd_rust = meson.get_compiler('c').find_library('std-abcdefgh')

librust = static_library(
  'rust',
  'librust.rs',
  rust_crate_type : 'object',
  dependencies: libstd-rust
)

user = executable(
  'user,
  'user.c',
  link_with : librust)
```
