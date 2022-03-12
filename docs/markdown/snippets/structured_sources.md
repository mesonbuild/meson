## structured_sources()

A new function, `structured_sources()` has been added. This function allows
languages like Rust which depend on the filesystem layout at compile time to mix
generated and static sources.

```meson
executable(
  'main',
  structured_sources(
    'main.rs,
    {'mod' : generated_mod_rs},
  )
)
```

Meson will then at build time copy the files into the build directory (if
necessary), so that the desired file structure is laid out, and compile that. In
this case:

```
root/
  main.rs
  mod/
    mod.rs
```
