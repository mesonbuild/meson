## Dist scripts

You can now specify scripts that are run as part of the `dist`
target. An example usage would go like this:

```meson
project('foo', 'c')

# other stuff here

meson.add_dist_script('dist_cleanup.py')
```
