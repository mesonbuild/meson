## System wide and user local cross files

Meson has gained the ability to load cross files from predefined locations
without passing a full path on Linux and the BSD OSes. User local files will be
loaded from `$XDG_DATA_HOME/meson/cross`, or if XDG_DATA_HOME is undefined,
`~/.local/share/meson/cross` will be used.

For system wide paths the values of `$XDG_DATA_DIRS` + `/meson/cross` will be used,
if XDG_DATA_DIRS is undefined then `/usr/local/share/meson/cross:/usr/share/meson/cross`
will be used instead.

A file relative to the current working directory will be tried first, then the
user specific path will be tried before the system wide paths.

Assuming that a file x86-linux is located in one of those places a cross build
can be started with:

```sh
meson builddir/ --cross-file x86-linux
```
