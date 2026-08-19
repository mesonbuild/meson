## `configure_file()` can require all configuration keys to be used

`configure_file()` now accepts a `strict` keyword argument. When
`strict: true` is set, configuration fails if any key in the
`configuration:` object is not used by the input template.

This covers `@KEY@` and `#mesondefine` substitutions, as well as the
cmake equivalents (`${KEY}`, `@KEY@` with `format: 'cmake@'`, and
`#cmakedefine`). The default remains `false` for backwards compatibility.

```meson
conf = configuration_data()
conf.set('FOO', 1)
conf.set('BAR', 0)
# Fails if BAR is not referenced in config.h.in
configure_file(input: 'config.h.in', output: 'config.h',
               configuration: conf, strict: true)
```
