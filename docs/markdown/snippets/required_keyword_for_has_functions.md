## All compiler `has_*` methods support the `required` keyword

Now instead of

```meson
assert(cc.has_function('some_function'))
assert(cc.has_type('some_type'))
assert(cc.has_member('struct some_type', 'x'))
assert(cc.has_members('struct some_type', ['x', 'y']))
```

we can use

```meson
cc.has_function('some_function', required: true)
cc.has_type('some_type', required: true)
cc.has_member('struct some_type', 'x', required: true)
cc.has_members('struct some_type', ['x', 'y'], required: true)
```
