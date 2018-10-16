## new compiler method `get_argument_syntax`

The compiler object now has `get_argument_syntax` method, which returns a
string value of `gcc`, `msvc`, or an undefined value string value. This can be
used to determine if a compiler uses gcc syntax (`-Wfoo`), msvc syntax
(`/w1234`), or some other kind of arguments.

```meson
cc = meson.get_compiler('c')

if cc.get_argument_syntax() == 'msvc'
  if cc.has_argument('/w1235')
    add_project_arguments('/w1235', language : ['c'])
  endif
elif cc.get_argument_syntax() == 'gcc'
  if cc.has_argument('-Wfoo')
    add_project_arguments('-Wfoo', language : ['c'])
  endif
elif cc.get_id() == 'some other compiler'
  add_project_arguments('--error-on-foo', language : ['c'])
endif
```
