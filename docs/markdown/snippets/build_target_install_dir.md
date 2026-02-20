## BuildTarget(install_dir) length > 1 replaced with keywords

Build Targets currently support (with limited documentation), passing an array
of more than one element to `install_dir:` (except for in some wrappers), and
will map these additional install_dir's to extra outputs. This is only used by vala, and has been replaced by explicit keyword arguments.

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
  install_vala_header_dir : get_option('includedir') / 'foo
)
```

Note that now you only need to specify values you want to deviate from the default.
