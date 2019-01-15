## install_man now accepts custom targets

The install_man function previously only accepted static files, it now accepts
custom_targets as well.

```meson
c = custom_target(
  'foo',
  ...
  output : 'foo.1',
)
install_man(c)
```
