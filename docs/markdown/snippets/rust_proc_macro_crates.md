## Rust proc-macro crates

Rust has these handy things called proc-macro crates, which are a bit like a
compiler plugin. We can now support them, simply build a [[shared_library]] with
the `rust_crate_type` set to `proc-macro`.

```meson
proc = shared_library(
  'proc',
  'proc.rs',
  rust_crate_type : 'proc-macro',
  install : false,
)

user = executable('user, 'user.rs', link_with : proc)
```
