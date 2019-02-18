## `introspect --targets` can now be used without configured build directory

It is now possible to run `meson introspect --targets /path/to/meson.build`
without a configured build directory.

The generated output is similar to running the introspection with a build
directory. However, there are some key differences:

- The paths in `filename` now are _relative_ to the future build directory
- The `install_filename` key is completely missing
- There is only one entry in `target_sources`:
  - With the language set to `unknown`
  - Empty lists for `compiler` and `parameters` and `generated_sources`
  - The `sources` list _should_ contain all sources of the target

There is no guarantee that the sources list in `target_sources` is correct.
There might be differences, due to internal limitations. It is also not
guaranteed that all targets will be listed in the output. It might even be
possible that targets are listed, which won't exist when meson is run normally.
This can happen if a target is defined inside an if statement.
Use this feature with care.