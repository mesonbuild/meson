## Default_options and override_options as dictionary

Currently the `default_options` and `override_options` values must be passed
as arrays of strings with and `=` in them:

```meson
project(
    'myproject',
    default_options : ['c_std=c99']
)
```

Now they may be passed as a dictionary instead:

```meson
project(
    'myproject',
    default_options : {'c_std' : 'c99'}
)
```
