## Vala BuildTarget dependency enhancements

A BuildTarget that has Vala sources can now get a File dependency for its
generated header, vapi, and gir files.

```meson
lib = library('foo', 'foo.vala')
lib_h = lib.vala_header()
lib_s = static_lib('static', 'static.c', lib_h)

lib_vapi = lib.vala_vapi()

custom_target(
  'foo-typelib',
  command : ['g-ir-compiler', '--output', '@OUTPUT@', '@INPUT@'],
  input : lib.vala_gir(),
  output : 'Foo-1.0.typelib'
)
```

`static.c` will not start compilation until `lib.h` is generated.
