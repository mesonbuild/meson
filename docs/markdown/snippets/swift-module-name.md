## Explicitly setting Swift module name is now supported

It is now possible to set the Swift module name for a target via the
*swift_module_name* target kwarg, overriding the default inferred from the
target name.

```meson
lib = library('foo', 'foo.swift', swift_module_name: 'Foo')
```
