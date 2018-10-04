# External Project module

*This is an experimental module, API could change.*

This module allows building code that uses build systems other than Meson. This
module is intended to be used to build Autotools subprojects as fallback if the
dependency couldn't be found on the system (e.g. too old distro version).

The project will be compiled out-of-tree inside Meson's build directory. The
project will also be installed inside Meson's build directory using make's
[`DESTDIR`](https://www.gnu.org/prep/standards/html_node/DESTDIR.html)
feature, so no root permission is required even if the installation prefix is
for example `/usr`.

Known limitations:
- Executables from external projects cannot be used uninstalled, because they
  would need its libraries to be installed in the final location. This is why
  there is no `find_program()` method.
- The configure script must generate a `Makefile`, other build systems are not
  yet supported.

*Added 0.55.0*

## Functions

### `add_project()`

This function should be called at the root directory of a project using another
build system. Usually in a `meson.build` file placed in the top directory of a
subproject, but could be also in any subdir.

Its first positional argument is the name of the configure script to be
executed (e.g. `configure` or `autogen.sh`), that file must be in the current
directory and executable.

Keyword arguments:
- `options`: An array of strings to be passed as arguments to the configure
  script. Some special tags will be replaced by Meson before passing them to
  the configure script: `{prefix}`, `{libdir}` and `{includedir}`. Note that
  `libdir` and `includedir` paths are relative to `prefix` in Meson but some
  configure scripts requires absolute path, in that case they can be passed as
  `'--libdir=' + join_paths('{prefix}', '{libdir}')`.
- `cross_options`: Extra options appended to `options` only when cross compiling.
  special tag `{host}` will be replaced by `'{}-{}-{}'.format(
  host_machine.cpu_family(), build_machine.system(), host_machine.system()`. If
  omitted it defaults to `['--host={host}']`.
- `verbose`: If set to `true` the output of sub-commands ran to configure, build
  and install the project will be printed onto Meson's stdout.

Returns an [`ExternalProject`](#ExternalProject_object) object

## `ExternalProject` object

### Methods

#### `dependency(libname)`


Return a dependency object that can be used to build targets against a library
from the external project.

Keyword arguments:
- `subdir` path relative to `includedir` to be added to the header search path.

## Example `meson.build` file for a subproject

```meson
project('My Autotools Project', 'c',
  meson_version : '>=0.55.0',
)

mod = import('unstable_external_project')

p = mod.add_project('configure',
  options : ['--prefix={prefix}',
             '--libdir={libdir}',
             '--incdir={includedir}',
             '--enable-foo',
            ],
)

mylib_dep = p.dependency('mylib')
```

## Using wrap file

Most of the time the project will be built as a subproject, and fetched using
a `.wrap` file. In that case the simple `meson.build` file needed to build the
subproject can be provided by adding `meson_filename=path/to/meson.build` line
in the wrap file, which is easier than providing a patch file.
