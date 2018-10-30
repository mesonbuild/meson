## Joining paths with /

Joining two paths has traditionally been done with the `join_paths` function.

```meson
joined = join_paths('foo', 'bar')
```

Now you can use the simpler notation using the `/` operator.

```meson
joined = 'foo' / 'bar'
```

This only works for strings.
