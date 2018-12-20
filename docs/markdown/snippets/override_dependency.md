## Can override `dependency()`

It is now possible to override the result of `dependency()` to point
to any dependency object you want. The overriding is global and applies to
every subproject from there on. Here is how you would use it.

In master project

```meson
subproject('glib')
```

In the called subproject:

```meson
libglib = library('glib-2.0', ...)
glib_dep = declare_dependency(link_with : libglib)
meson.override_dependency('glib-2.0', glib_dep)
```

In master project (or, in fact, any subproject):

```meson
glib_dep = dependency('glib-2.0')
```

Now `glib_dep` points to the internal dependency from the subproject, and not
the external dependency from the system `glib-2.0.pc` pkg-config file.
