## `meson format` suppression directives

`meson format` now leaves untouched the lines between
`# meson-format off` and `# meson-format on` comments. When
`# meson-format off` is not followed by `# meson-format on`, formatting
is disabled until the end of the file. `muon fmt`'s `# fmt: off` and
`# fmt: on` directives are also recognized.

```meson
# meson-format off
sources = files(
  'a.c',      'b.c',
  'c.c',      'd.c',
)
# meson-format on
```
