## Required kwarg on more `compiler` methods

The following `compiler` methods now support the `required` keyword argument:

- `compiler.compiles()`
- `compiler.links()`
- `compiler.runs()`

```meson
cc.compiles(valid, name: 'valid', required : true)
cc.links(valid, name: 'valid', required : true)
cc.run(valid, name: 'valid', required : true)

assert(not cc.compiles(valid, name: 'valid', required : opt))
assert(not cc.links(valid, name: 'valid', required : opt))
res = cc.run(valid, name: 'valid', required : opt)
assert(res.compiled())
assert(res.returncode() == 0)
assert(res.stdout() == '')
assert(res.stderr() == '')
```
