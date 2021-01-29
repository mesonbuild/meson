## Specify DESTDIR on command line

`meson install` command now has `--destdir` argument that overrides DESTDIR
from environment.

## Skip install scripts if DESTDIR is set

`meson.add_install_script()` now has `skip_if_destdir` keyword argument. If set
to `true` the script won't be run if DESTDIR is set during installation. This is
useful in the case the script updates system wide cache that is only needed when
copying files into final destination.
