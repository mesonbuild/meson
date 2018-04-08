## Can override find_program

It is now possible to override the result of `find_program` to point
to a custom program you want. The overriding is global and applies to
every subproject from there on. Here is how you would use it.

In master project

```meson
subproject('mydep')
```

In the called subproject:

```meson
prog = find_program('my_custom_script')
meson.override_find_program('mycodegen', prog)
```

In master project (or, in fact, any subproject):

```meson
genprog = find_program('mycodegen')
```

Now `genprog` points to the custom script. If the dependency had come
from the system, then it would point to the system version.
