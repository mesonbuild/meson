## String concatenation in meson_options.txt

It is now possible to use string concatenation (with the `+` opperator) in the
meson_options.txt file. This allows splitting long option descriptions.

```meson
option(
  'testoption',
  type : 'string',
  value : 'optval',
  description : 'An option with a very long description' +
                'that does something in a specific context'
)
```
