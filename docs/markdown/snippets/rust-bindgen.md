## Rust.bindgen improvements

The rust module's bindgen wrapper now supports convenience arguments for
`--allowlist-*` and `--blocklist-*`.

These are in the form:
```meson
rust.bindgen(
  ...,
  allowlist : {'var': ['pub_*']}
)
```

Additionally, a wrapper for `--clang-macro-fallback` has been added which also
sets the build dir to the target's private directory.
