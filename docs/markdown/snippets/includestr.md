## `include_directories` accepts a string

The `include_directories` keyword argument now accepts plain strings
rather than an include directory object. Meson will transparently
expand it so that a declaration like this:

```meson
executable(..., include_directories: 'foo')
```

Is equivalent to this:

```meson
foo_inc = include_directories('foo')
executable(..., include_directories: inc)
```
