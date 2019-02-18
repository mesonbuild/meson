## `introspect --dependencies` can now be used without configured build directory

It is now possible to run `meson introspect --dependencies /path/to/meson.build`
without a configured build directory.

However, the generated output is vastly different from running the introspection
command with a build directory.

The output format is as follows:

```json
[
  {
    "name": "The name of the dependency",
    "required": true,
    "conditional": false,
    "has_fallback": false
  }
]
```

The `required` keyword specifies whether the dependency is marked as required
in the `meson.build` (all dependencies are required by default). The
`conditional` key indicates whether the `dependency()` function was called
inside a conditional block. In a real meson run these dependencies might not be
used, thus they _may_ not be required, even if the `required` key is set. The
`has_fallback` key just indicates whether a fallback was directly set in the
`dependency()` function.