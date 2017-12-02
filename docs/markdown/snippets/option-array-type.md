# An array type for user options

Previously to have an option that took more than one value a string value would
have to be created and split, but validating this was difficult. A new array type
has been added to the meson_options.txt for this case. It works like a 'combo', but
allows more than one option to be passed. When used on the command line (with -D),
values are passed as a comma separated list.

```meson
option('array_opt', type : 'array', choices : ['one', 'two', 'three'], value : ['one'])
```

These can be overwritten on the command line,

```meson
meson _build -Darray_opt=two,three
```
