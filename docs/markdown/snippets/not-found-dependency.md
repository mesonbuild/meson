# Not-found dependency objects

```meson
dep = dependency('', required:false)
```

can now be more simply written as

```meson
dep = dependency()
```

which can be used to represent a disabled dependency, and is safe to call
`found()` on, unlike `[]'.
