## Vala BuildTarget dependency enhancements

A BuildTarget that has Vala sources can now get a File dependency for its
generated header.

```meson
lib = library('foo', 'foo.vala')
lib_h = lib.vala_header()
lib_s = static_lib('static', 'static.c', lib_h)
```

`static.c` will not start compilation until `lib.h` is generated.
