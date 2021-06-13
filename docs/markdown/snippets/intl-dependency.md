## New custom dependency for libintl

Meson can now find the library needed for translating messages via gettext.
This works both on systems where libc provides gettext, such as GNU or musl,
and on systems where the gettext project's standalone intl support library is
required, such as macOS.

Rather than doing something such as:

```
intl_dep = dependency('', required: false)

if cc.has_function('ngettext')
  intl_found = true
else
  intl_dep = cc.find_library('intl', required: false)
  intl_found = intl_dep.found()
endif

if intl_found
  # build options that need gettext
  conf.set('ENABLE_NLS', 1)
endif
```
  
one may simply use:

```
intl_dep = dependency('intl')

if intl_dep.found()
  # build options that need gettext
  conf.set('ENABLE_NLS', 1)
endif
```
