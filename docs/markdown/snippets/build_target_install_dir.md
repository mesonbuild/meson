## BuildTarget(install_dir) length > 1 replaced with keywords

Build targets previously supported (with limited documentation) passing an array
of more than one element to `install_dir:` (except in some wrappers), and
would map these additional `install_dir`s to extra outputs. This was only used by
Vala, and separate explicit keyword arguments are now available that provide
the same functionality.

Code like this:
```meson
library(
  'foo',
  'foo.vala',
  install : true,
  install_dir : [true, get_option('includedir') / 'foo', true],
)
```

should now be written as the much clearer:

```meson
library(
  'foo',
  'foo.vala',
  install : true,
  install_vala_header : get_option('includedir') / 'foo',
  install_vala_vapi : true,
)
```

Note that the default is `false` for the Vala extra outputs.
