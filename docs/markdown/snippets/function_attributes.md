## Helper methods added for checking GNU style attributes: __attribute__(...)

A set of new helpers have been added to the C and C++ compiler objects for
checking GNU style function attributes. These are not just simpler to use, they
may be optimized to return fast on compilers that don't support these
attributes. Currently this is true for MSVC.

```meson
cc = meson.get_compiler('c')
if cc.has_function_attribute('aligned')
   add_project_arguments('-DHAVE_ALIGNED', language : 'c')
endif
```

Would replace code like:

```meson
if cc.compiles('''into foo(void) __attribute__((aligned(32)))''')
   add_project_arguments('-DHAVE_ALIGNED', language : 'c')
endif
```

Additionally, a multi argument version has been added:

```meson
foreach s : cc.get_supported_function_attributes(['hidden', 'alias'])
   add_project_arguments('-DHAVE_@0@'.format(s.to_upper()), language : 'c')
endforeach
```
