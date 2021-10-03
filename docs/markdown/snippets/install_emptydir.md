## install_emptydir function

It is now possible to define a directory which will be created during
installation, without creating it as a side effect of installing files into it.
This replaces custom `meson.add_install_script()` routines. For example:

```meson
meson.add_install_script('sh', '-c', 'mkdir -p "$DESTDIR/@0@"'.format(path))
```

can be replaced by:

```meson
install_emptydir(path)
```

and as a bonus this works reliably on Windows, prints a sensible progress
message, will be uninstalled by `ninja uninstall`, etc.
