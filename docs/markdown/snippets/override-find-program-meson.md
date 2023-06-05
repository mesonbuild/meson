## New override of `find_program('meson')`

In some cases, it has been useful for build scripts to access the Meson command
used to invoke the build script. This has led to various ad-hoc solutions that
can be very brittle and project-specific.

```meson
meson_prog = find_program('meson')
```

This call will supply the build script with an external program pointing at the
invoked Meson.

Because Meson also uses `find_program` for program lookups internally, this
override will also be handled in cases similar to the following:

```meson
custom_target(
  # ...
  command: [
    'meson',
  ],
  # ...
)

run_command(
  'meson',
  # ...
)

run_target(
  'tgt',
  command: [
    'meson',
    # ...
  ]
)
```
