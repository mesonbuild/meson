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
