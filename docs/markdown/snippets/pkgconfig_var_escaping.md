## Unescaped variables in pkgconfig files

Spaces in variable values are escaped with `\`, this is required in the case the
value is a path that and is used in `cflags` or `libs` arguments. This was an
undocumented behaviour that caused issues in the case the variable is a space
separated list of items.

For backward compatibility reasons this behaviour could not be changed, new
keyword arguments have thus been added: `unescaped_variables` and
`unescaped_uninstalled_variables`.

```meson
pkg = import('pkgconfig')
...
pkg.generate(lib,
  variables: {
    'mypath': '/path/with spaces/are/escaped',
  },
  unescaped_variables: {
    'mylist': 'Hello World Is Not Escaped',
  },
)
```
