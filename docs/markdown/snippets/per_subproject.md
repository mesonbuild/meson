## Per subproject `warning_level` and compiler options

`warning_level` and compiler options can now be defined per subproject, in the
same way as `default_library` and `werror`.

In particular this allows for subprojects to build with different `c_std` and
`cpp_std` versions. In the example below, `modern-cpp-project` subproject used
to inherit c++98 std from its parent project and would usually fail to build,
but it would now build with its own std version instead.

Main project `meson.build`:
```meson
project('main project', 'cpp', default_options: ['cpp_std=c++98'])
subproject('modern-cpp-project')
```

Subproject `meson.build`:
```meson
project('modern-cpp-project', 'cpp', default_options: ['cpp_std=c++17'])
```

Note that this does not include `<lang>_args` and `<lang>_link_args`
(e.g. `c_args`, `c_link_args`) which are still global options.
