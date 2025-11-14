## Added OS/2 support

Meson now supports OS/2 system. Especially, `shortname` kwarg and
`os2_emxomf` builtin option are introduced.

`shortname` is used to specify a short DLL name fitting to a 8.3 rule.

```meson
lib = library('foo_library',
    ...
    shortname: 'foo',
    ...
)
```

This will generate `foo.dll` not `foo_library.dll` on OS/2. If
`shortname` is not used, `foo_libr.dll` which is truncated up to 8
characters is generated.

`os2_emxomf` is used to generate OMF files with OMF tool-chains.

```
meson setup --os2-emxomf builddir
```

This will generate OMF object files and `.lib` library files. If
`--os2-emxomf` is not used, AOUT object files and `.a` library files are
generated.
