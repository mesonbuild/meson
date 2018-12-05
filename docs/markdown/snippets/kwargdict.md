## Can specify keyword arguments with a dictionary

You can now specify keyword arguments for any function and method call
with the `kwargs` keyword argument. This is perhaps best described
with an example:

```meson
options = {'include_directories': include_directories('inc')}

...

executable(...
  kwargs: options)
```

The above code is identical to this:

```meson
executable(...
  include_directories: include_directories('inc'))
```

That is, Meson will expand the dictionary given to `kwargs` as if the
entries in it had been given as keyword arguments directly.

Note that any individual argument can be specified either directly or
with the `kwarg` dict but not both. If a key is specified twice, it
is a hard error.
