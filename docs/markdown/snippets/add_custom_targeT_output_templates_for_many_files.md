## `custom_target` gains `output` templates for multiple files

Currently, if you have a target with multiple outputs, you have to manually list
them all, even if they are using a `@PLAINNAME@` or `@BASENAME@` scheme. Now,
Meson will handle that scheme for multiple files as well with the `@PLAINNAMES@`
and `@BASENAMES@` value, like so:

```meson
custom_target(
  output : '@PLAINNAMES@.out',
  input : ['a.in', 'b.in', 'c.in'],
  command : [find_program('input-compiler), '@OUTDIR@', '@INPUT@'],
)
```

Meson will convert this to `output : ['a.out', 'b.out', 'c.out']` automatically.
