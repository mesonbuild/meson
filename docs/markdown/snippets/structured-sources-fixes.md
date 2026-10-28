## `structured_sources()` is now checked and copies files when needed

A bugs in `structured_sources()` has been fixed which can cause a Rust
target to be built from a different set of files than before.
In particular, the check to detect whether source files have to be copied
to the build directory was previously wrong, and calls that only move
around source files require Meson 1.13.0 or newer.  For example:

```meson
structured_sources(['main.rs'], {'foo': 'linux/foo.rs'})
```

did not place `linux/foo.rs` in `foo.rs`, and `mod foo;` failed to compile.
The layout is now the same whether the structure contains generated
files or not, and files are copied requested layout differs from the
layout in the source directory.
