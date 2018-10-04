## External projects

A new experimental module `unstable_external_project` has been added to build
code using other build systems than Meson. Currently only supporting projects
with a configure script that generates Makefiles.

```meson
project('My Autotools Project', 'c',
  meson_version : '>=0.56.0',
)

mod = import('unstable_external_project')

p = mod.add_project('configure',
  configure_options : ['--prefix=@PREFIX@',
                       '--libdir=@LIBDIR@',
                       '--incdir=@INCLUDEDIR@',
                       '--enable-foo',
                      ],
)

mylib_dep = p.dependency('mylib')
```

