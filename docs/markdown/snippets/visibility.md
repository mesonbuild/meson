## Keyword argument for symbol visibility

Build targets got a new keyword, `symbol_visibility` that controls how
symbols are exported from shared libraries. This is most commonly used
to hide implementation symbols like this:

```meson
shared_library('mylib', ...
  symbol_visibility: 'hidden')
```

In this case only symbols explicitly marked as visible in the source
files get exported.
