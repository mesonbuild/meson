## project() can now accept languages per-machine

```meson
project(
  'foo',
  'c',  # for both machines
  host_machine_languages : ['objc'],  # only for the host
  build_machine_languages : ['cpp'],  # only for the builder
)
```

Which would be equivalent to:
```meson
project('foo', 'c')
add_languages('objc', required : true, native : false)
add_languages('cpp', required : true, native : true)
```
