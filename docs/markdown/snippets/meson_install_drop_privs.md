## `sudo meson install` now drops privileges when rebuilding targets

It is common to install projects using sudo, which should not affect build
outputs but simply install the results. Unfortunately, since the ninja backend
updates a state file when run, it's not safe to run ninja as root at all.

It has always been possible to carefully build with:

```
ninja && sudo meson install --no-rebuild
```

Meson now tries to be extra safe as a general solution. `sudo meson install`
will attempt to rebuild, but has learned to run `ninja` as the original
(pre-sudo or pre-doas) user, ensuring that build outputs are generated/compiled
as non-root.
