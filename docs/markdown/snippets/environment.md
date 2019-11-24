## environment() now had `separator` and `method` keyword arguments

This is useful to control how initial values are added. `method` must be one of
'set', 'prepend' or 'append' strings.

```meson
environment({'MY_VAR': ['a', 'b']}, method: 'prepend', separator=',')
```

## Uninstalled environment

It is often useful for developers to run the project without having to install it.
But to work, many projects needs to set some environment variables, such as location
in the build directory of plugins, or adding some built tools location to PATH.

Meson makes it easy by allowing projects to define those variables directly from the
build definition, using `meson.add_uninstalled_environment()` method. Developers
can then run a command inside that environment using `meson uninstalled` command line.

For example, if a project builds an executable that needs data files from source
directory:
```meson
project(...)
tool = executable('mytool', ...)
meson.add_uninstalled_environment({
    'PATH': meson.current_build_dir(),
    'MYTOOL_DATA_DIR': meson.current_source_dir() / 'data',
  },
  method: 'prepend',
)
```

Developers can then test it from the command line: `meson uninstalled -C builddir mytool`.
