# Command-line commands

There are two different ways of invoking Meson. First, you can run it
directly from the source tree with the command
`/path/to/source/meson.py`. Meson may also be installed in which case
the command is simply `meson`. In this manual we only use the latter
format for simplicity.

Meson is invoked using the following syntax:
`meson [COMMAND] [COMMAND_OPTIONS]`

This section describes all available commands and some of their
Optional arguments. The most common workflow is to run
[`setup`](#setup), followed by [`compile`](#compile), and then
[`install`](#install).

For the full list of all available options for a specific command use
the following syntax: `meson COMMAND --help`

### configure

{{ configure_usage.inc }}

Changes options of a configured meson project.

{{ configure_arguments.inc }}

Most arguments are the same as in [`setup`](#setup).

Note: reconfiguring project will not reset options to their default
values (even if they were changed in `meson.build`).

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

{{ compile_usage.inc }}

Builds a default or a specified target of a configured meson project.

{{ compile_arguments.inc }}

`--verbose` argument is available since 0.55.0.

#### Targets

*(since 0.55.0)*

`TARGET` has the following syntax `[PATH/]NAME[:TYPE]`, where:
- `NAME`: name of the target from `meson.build` (e.g. `foo` from `executable('foo', ...)`).
- `PATH`: path to the target relative to the root `meson.build` file. Note: relative path for a target specified in the root `meson.build` is `./`.
- `TYPE`: type of the target. Can be one of the following: 'executable', 'static_library', 'shared_library', 'shared_module', 'custom', 'run', 'jar'.
  
`PATH` and/or `TYPE` can be omitted if the resulting `TARGET` can be
used to uniquely identify the target in `meson.build`.

#### Backend specific arguments

*(since 0.55.0)*

`BACKEND-args` use the following syntax:

If you only pass a single string, then it is considered to have all
values separated by commas. Thus invoking the following command:

```
$ meson compile --ninja-args=-n,-d,explain
```

would add `-n`, `-d` and `explain` arguments to ninja invocation.

If you need to have commas or spaces in your string values, then you
need to pass the value with proper shell quoting like this:

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

Build three targets: two targets that have the same `foo` name, but
different type, and a `bar` target:

```
meson compile foo:shared_library foo:static_library bar
```

Produce a coverage html report (if available):

```
meson compile coverage-html
```

### dist

*(since 0.52.0)*

{{ dist_usage.inc }}

Generates a release archive from the current source tree.

{{ dist_arguments.inc }}

See [notes about creating releases](Creating-releases.md) for more info.

#### Examples:

Create a release archive:
```
meson dist -C builddir
```

### init

*(since 0.45.0)*

{{ init_usage.inc }}

Creates a basic set of build files based on a template.

{{ init_arguments.inc }}

#### Examples:

Create a project in `sourcedir`:
```
meson init -C sourcedir
```

### introspect

{{ introspect_usage.inc }}

Displays information about a configured meson project.

{{ introspect_arguments.inc }}

#### Examples:

Display basic information about a configured project in `builddir`:

```
meson introspect builddir --projectinfo
```

### install

*(since 0.47.0)*

{{ install_usage.inc }}

Installs the project to the prefix specified in [`setup`](#setup).

{{ install_arguments.inc }}

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

{{ rewrite_usage.inc }}

Modifies the meson project.

{{ rewrite_arguments.inc }}

See [the meson file rewriter documentation](Rewriter.md) for more info.

### setup

{{ setup_usage.inc }}

Configures a build directory for the meson project.

This is the default meson command (invoked if there was no COMMAND supplied).

{{ setup_arguments.inc }}

See [meson introduction
page](Running-Meson.md#configuring-the-build-directory) for more info.

#### Examples:

Configures `builddir` with default values:
```
meson setup builddir
```

### subprojects

*(since 0.49.0)*

{{ subprojects_usage.inc }}

Manages subprojects of the meson project.

{{ subprojects_arguments.inc }}

### test

{{ test_usage.inc }}

Run tests for the configure meson project.

{{ test_arguments.inc }}

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

{{ wrap_usage.inc }}

An utility to manage WrapDB dependencies.

{{ wrap_arguments.inc }}

See [the WrapDB tool documentation](Using-wraptool.md) for more info.
