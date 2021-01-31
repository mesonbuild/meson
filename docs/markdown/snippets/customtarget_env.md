## `custom_target()` now accepts an `env` keyword argument

Environment variables can now be passed to the `custom_target()` command.

```meson
env = environment()
env.append('PATH', '/foo')
custom_target(..., env: env)
custom_target(..., env: {'MY_ENV': 'value'})
custom_target(..., env: ['MY_ENV=value'])
```
