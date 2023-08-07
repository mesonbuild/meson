## `fs.relative_to()`

The `fs` module now has a `relative_to` method. The method will return the
relative path from argument one to argument two, if one exists. Otherwise, the
absolute path to argument one is returned.

```meson
assert(fs.relative_to('c:\\prefix\\lib', 'c:\\prefix\\bin') == '..\\lib')
assert(fs.relative_to('c:\\proj1\\foo', 'd:\\proj1\\bar') == 'c:\\proj1\\foo')
assert(fs.relative_to('prefix\\lib\\foo', 'prefix') == 'lib\\foo')

assert(fs.relative_to('/prefix/lib', '/prefix/bin') == '../lib')
assert(fs.relative_to('prefix/lib/foo', 'prefix') == 'lib/foo')
```

In addition to strings, it can handle files, custom targets, custom target
indices, and build targets.
