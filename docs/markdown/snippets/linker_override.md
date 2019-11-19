## Generic Overrider for Dynamic Linker selection

Previous to meson 0.52.0 you set the dynamic linker using compiler specific
flags passed via language flags and hoped things worked out. In meson 0.52.0
meson started detecting the linker and making intelligent decisions about
using it. Unfortunately this broke choosing a non-default linker.

Now there is a generic mechanism for doing this, you may use the LD
environment variable (with normal meson environment variable rules), or add
the following to a cross or native file:

```ini
[binaries]
ld = 'gold'
```

And meson will select the linker if possible.
