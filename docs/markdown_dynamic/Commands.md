# Command-line commands

There are two different ways of invoking Meson. First, you can run it directly
from the source tree with the command `/path/to/source/meson.py`. Meson may
also be installed in which case the command is simply `meson`. In this manual
we only use the latter format for simplicity.

Meson is invoked using the following syntax:
`meson [COMMAND] [COMMAND_OPTIONS]`

This section describes all available commands and some of their Optional arguments.
The most common workflow is to run [`setup`](#setup), followed by [`compile`](#compile), and then [`install`](#install).

For the full list of all available options for a specific command use the following syntax:
`meson COMMAND --help`

### configure

```
{{ cmd_help['configure']['usage'] }}
```

Changes options of a configured meson project.

```
{{ cmd_help['configure']['arguments'] }}
```

Most arguments are the same as in [`setup`](#setup).

Note: reconfiguring project will not reset options to their default values (even if they were changed in `meson.build`).

#### Examples:

List all available options:
```
meson configure builddir
```

Change value of a single option:
```
meson configure builddir -Doption=new_value
```

### compile

*(since 0.54.0)*

```
{{ cmd_help['compile']['usage'] }}
```

Builds a default or a specified target of a configured meson project.

```
{{ cmd_help['compile']['arguments'] }}
```

`--verbose` argument is available since 0.55.0.

#### Targets

*(since 0.55.0)*

`TARGET` has the following syntax `[PATH/]NAME[:TYPE]`, where:
- `NAME`: name of the target from `meson.build` (e.g. `foo` from `executable('foo', ...)`).
- `PATH`: path to the target relative to the root `meson.build` file. Note: relative path for a target specified in the root `meson.build` is `./`.
- `TYPE`: type of the target. Can be one of the following: 'executable', 'static_library', 'shared_library', 'shared_module', 'custom', 'run', 'jar'.
  
`PATH` and/or `TYPE` can be ommited if the resulting `TARGET` can be used to uniquely identify the target in `meson.build`.

#### Backend specific arguments

*(since 0.55.0)*

`BACKEND-args` use the following syntax:

If you only pass a single string, then it is considered to have all values separated by commas. Thus invoking the following command:

```
$ meson compile --ninja-args=-n,-d,explain
```

would add `-n`, `-d` and `explain` arguments to ninja invocation.

If you need to have commas or spaces in your string values, then you need to pass the value with proper shell quoting like this:

```
$ meson compile "--ninja-args=['a,b', 'c d']"
```

#### Examples:

Build the project:
```
meson compile -C builddir
```

Execute a dry run on ninja backend with additional debug info:
```
meson compile --ninja-args=-n,-d,explain
```

Build three targets: two targets that have the same `foo` name, but different type, and a `bar` target:
```
meson compile foo:shared_library foo:static_library bar
```

Produce a coverage html report (if available):
```
meson compile coverage-html
```

### dist

*(since 0.52.0)*

```
{{ cmd_help['dist']['usage'] }}
```

Generates a release archive from the current source tree.

```
{{ cmd_help['dist']['arguments'] }}
```

See [notes about creating releases](Creating-releases.md) for more info.

#### Examples:

Create a release archive:
```
meson dist -C builddir
```

### init

*(since 0.45.0)*

```
{{ cmd_help['init']['usage'] }}
```

Creates a basic set of build files based on a template.

```
{{ cmd_help['init']['arguments'] }}
```

#### Examples:

Create a project in `sourcedir`:
```
meson init -C sourcedir
```

### introspect

```
{{ cmd_help['introspect']['usage'] }}
```

Displays information about a configured meson project.

```
{{ cmd_help['introspect']['arguments'] }}
```

#### Examples:

Display basic information about a configured project in `builddir`:
```
meson introspect builddir
```

### install

*(since 0.47.0)*

```
{{ cmd_help['install']['usage'] }}
```

Installs the project to the prefix specified in [`setup`](#setup).

```
{{ cmd_help['install']['arguments'] }}
```

See [the installation documentation](Installing.md) for more info.

#### Examples:

Install project to `prefix`:
```
meson install -C builddir
```

Install project to `$DESTDIR/prefix`:
```
DESTDIR=/path/to/staging/area meson install -C builddir
```

### rewrite

*(since 0.50.0)*

```
{{ cmd_help['rewrite']['usage'] }}
```

Modifies the meson project.

```
{{ cmd_help['rewrite']['arguments'] }}
```

See [the meson file rewriter documentation](Rewriter.md) for more info.

### setup

```
{{ cmd_help['setup']['usage'] }}
```

Configures a build directory for the meson project.

This is the default meson command (invoked if there was no COMMAND supplied).

```
{{ cmd_help['setup']['arguments'] }}
```

See [meson introduction page](Running-Meson.md#configuring-the-build-directory) for more info.

#### Examples:

Configures `builddir` with default values:
```
meson setup builddir
```

### subprojects

*(since 0.49.0)*

```
{{ cmd_help['subprojects']['usage'] }}
```

Manages subprojects of the meson project.

```
{{ cmd_help['subprojects']['arguments'] }}
```

### test

```
{{ cmd_help['test']['usage'] }}
```

Run tests for the configure meson project.

```
{{ cmd_help['test']['arguments'] }}
```

See [the unit test documentation](Unit-tests.md) for more info.

#### Examples:

Run tests for the project:
```
meson test -C builddir
```

Run only `specific_test_1` and `specific_test_2`:
```
meson test -C builddir specific_test_1 specific_test_2
```

### wrap

```
{{ cmd_help['wrap']['usage'] }}
```

An utility to manage WrapDB dependencies.

```
{{ cmd_help['wrap']['arguments'] }}
```

See [the WrapDB tool documentation](Using-wraptool.md) for more info.
