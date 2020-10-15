## Consistency between `declare_dependency()` and `pkgconfig.generate()` variables

The `variables` keyword argument in `declare_dependency()` used to only support
dictionary and `pkgconfig.generate()` only list of strings. They now both support
dictionary and list of strings in the format `'name=value'`. This makes easier
to share a common set of variables for both:

```meson
vars = {'foo': 'bar'}
dep = declare_dependency(..., variables: vars)
pkg.generate(..., variables: vars)
```
