## meson.add_*_script methods accept new types

All three (`add_install_script`, `add_dist_script`, and
`add_postconf_script`) now accept ExternalPrograms (as returned by
`find_program`), Files, and the output of `configure_file`. The dist and
postconf methods cannot accept other types because of when they are run.
While dist could, in theory, take other dependencies, it would require more
extensive changes, particularly to the backend.

```meson
meson.add_install_script(find_program('foo'), files('bar'))
meson.add_dist_script(find_program('foo'), files('bar'))
meson.add_postconf_script(find_program('foo'), files('bar'))
```

The install script variant is also able to accept custom_targets,
custom_target indexes, and build targets (executables, libraries), and can
use built executables a the script to run

```meson
installer = executable('installer', ...)
meson.add_install_script(installer, ...)
meson.add_install_script('foo.py', installer)
```
