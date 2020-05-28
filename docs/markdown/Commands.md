# Command-line commands

There are two different ways of invoking Meson. First, you can run it directly
from the source tree with the command `/path/to/source/meson.py`. Meson may
also be installed in which case the command is simply `meson`. In this manual
we only use the latter format for simplicity.

Meson is invoked using the following syntax:
`meson [COMMAND] [COMMAND_OPTIONS]`

This section describes all available commands and some of their notable options.
The most common workflow is to run [`setup`](#setup), followed by [`compile`](#compile), and then [`install`](#install).

For the full list of all available options for a specific command use the following syntax:
`meson COMMAND --help`

### compile

*(since 0.54.0)*

Builds a default or specified target of a configured meson project.

Syntax: `meson compile [TARGET [TARGET...]] [options]`  
Eample: `meson compile -C builddir`

Note: specifying a target is available since 0.55.0.

`TARGET` has the following syntax: `[PATH/]NAME[:TYPE]`.
`NAME`: name of the target from `meson.build` (e.g. `foo` from `executable('foo', ...)`).
`PATH`: path to the target relative to the root `meson.build` file. Note: relative path for a target specified in the root `meson.build` is `./`.
`TYPE`: type of the target (e.g. `shared_library`, `executable` and etc)

`PATH` and/or `TYPE` can be ommited if the resulting `TARGET` can be used to uniquely identify the target in `meson.build`.

For example targets from the following code:
```meson
shared_library('foo', ...)
static_library('foo', ...)
executable('bar', ...)
```
can be invoked with `meson compile foo:shared_library foo:static_library bar`.

Note: the following limitations for backends apply:
- `ninja`: `custom_target` is not supported.
- `vs`: `run_target` is not supported.

Notable options:
- `--jobs JOBS`: The number of worker jobs to run (if supported). If the value is less
                 than 1 the build program will guess.
- `--clean`: Cleans the build directory.

### dist

*(since 0.52.0)*

Generates a release archive from the current source tree.

Example: `meson dist -C builddir`

This creates a file called `projectname-version.tar.xz` in the build
tree subdirectory `meson-dist`. This archive contains the full
contents of the latest commit in revision control including all the
submodules (recursively). All revision control metadata is removed.
Meson then takes
this archive and tests that it works by doing a full compile + test +
install cycle. If all these pass, Meson will then create a SHA-256
checksum file next to the archive.

**Note**: Meson behaviour is different from Autotools. The Autotools
"dist" target packages up the current source tree. Meson packages
the latest revision control commit. The reason for this is that it
prevents developers from doing accidental releases where the
distributed archive does not match any commit in revision control
(especially the one tagged for the release).

Noteable options:
- `--include-subprojects`: Include source code of subprojects that have been used for the build.

### init

*(since 0.45.0)*

Creates a basic set of build files based on a template.

Example: `meson init -C sourcedir`

Notable options:
- `--name NAME`: project name. default: name of current directory.
- `--deps DEPS`: list of project dependencies, comma-separated.

### introspect

Displays information about a configured meson project.

Syntax: `meson introspect [builddir] INTROSPECT_COMMAND [introspect_command_options]`  
Example: `meson introspect builddir`

Notable introspect commands:
- `--buildoptions`: List all build options.
- `--dependencies`: List external dependencies.
- `--targets`: List top level targets.

### install

*(since 0.47.0)*

Installs the project to the prefix specified in `setup`.

Examples: 
- `meson install -C builddir`
- `DESTDIR=/path/to/staging/area meson install -C builddir`

See [the installation documentation](Installing.md) for more info.

### rewrite

*(since 0.50.0)*

Modifies the meson project.

See [the meson file rewriter documentation](Rewriter.md) for more info.

### setup

The default meson command (invoked if there was no COMMAND supplied).

Configures a build directory for the meson project.

Example: `meson setup builddir`

See [meson introduction page](Running-Meson.md#configuring-the-build-directory) for more info.

### subprojects

*(since 0.49.0)*

Manages subprojects of the meson project.

Syntax: `meson subprojects SUBPROJECTS_COMMAND [subprojects_command_options]`

Notable subprojects commands:
- `download`: Ensure subprojects are fetched, even if not in use. Already downloaded subprojects
              are not modified. This can be used to pre-fetch all subprojects and avoid
              downloads during configure.
- `foreach`: Execute a command in each subproject directory.

### test

Run tests for the configure meson project.

Example: `meson test -C builddir`

See [the unit test documentation](Unit-tests.md) for more info.

### wrap

An utility to manage WrapDB dependencies.

See [the WrapDB tool documentation](Using-wraptool.md) for more info.
