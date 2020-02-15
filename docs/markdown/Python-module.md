---
short-description: Generic python module
authors:
    - name: Mathieu Duponchelle
      email: mathieu@centricular.com
      years: [2018]
      has-copyright: false
...

# Python module

This module provides support for finding and building extensions against
python installations, be they python 2 or 3.

*Added 0.46.0*

## Functions

### `find_installation()`

``` meson
pymod.find_installation(name_or_path, ...)
```

Find a python installation matching `name_or_path`.

That argument is optional, if not provided then the returned python
installation will be the one used to run meson.

If provided, it can be:

- A simple name, eg `python-2.7`, meson will look for an external program
  named that way, using [find_program]

- A path, eg `/usr/local/bin/python3.4m`

- One of `python2` or `python3`: in either case, the module will try some
  alternative names: `py -2` or `py -3` on Windows, and `python` everywhere.
  In the latter case, it will check whether the version provided by the
  sysconfig module matches the required major version

Keyword arguments are the following:

- `required`: by default, `required` is set to `true` and Meson will
  abort if no python installation can be found. If `required` is set to `false`,
  Meson will continue even if no python installation was found. You can
  then use the `.found()` method on the returned object to check
  whether it was found or not. Since *0.48.0*  the value of a
  [`feature`](Build-options.md#features) option can also be passed to the
  `required` keyword argument.
- `disabler`: if `true` and no python installation can be found, return a
  [disabler object](Reference-manual.md#disabler-object) instead of a not-found object.
  *Since 0.49.0*
- `modules`: a list of module names that this python installation must have.
  *Since 0.51.0*

**Returns**: a [python installation][`python_installation` object]

## `python_installation` object

The `python_installation` object is an [external program], with several
added methods.

### Methods

#### `path()`

```meson
str py_installation.path()
```

*Added 0.50.0*

Works like the path method of other `ExternalProgram` objects. Was not
provided prior to 0.50.0 due to a bug.

#### `extension_module()`

``` meson
shared_module py_installation.extension_module(module_name, list_of_sources, ...)
```

Create a `shared_module` target that is named according to the naming
conventions of the target platform.

All positional and keyword arguments are the same as for [shared_module],
excluding `name_suffix` and `name_prefix`, and with the addition of the following:

- `subdir`: By default, meson will install the extension module in
  the relevant top-level location for the python installation, eg
  `/usr/lib/site-packages`. When subdir is passed to this method,
  it will be appended to that location. This keyword argument is
  mutually exclusive with `install_dir`

`extension_module` does not add any dependencies to the library so user may
need to add `dependencies : py_installation.dependency()`, see [][`dependency()`].

**Returns**: a [buildtarget object]

#### `dependency()`

``` meson
python_dependency py_installation.dependency(...)
```

This method accepts no positional arguments, and the same keyword arguments as
the standard [dependency] function. It also supports the following keyword
argument:

- `embed`: *(since 0.53.0)* If true, meson will try to find a python dependency
  that can be used for embedding python into an application.

**Returns**: a [python dependency][`python_dependency` object]

#### `install_sources()`

``` meson
void py_installation.install_sources(list_of_files, ...)
```

Install actual python sources (`.py`).

All positional and keyword arguments are the same as for [install_data],
with the addition of the following:

- `pure`: On some platforms, architecture independent files are expected
  to be placed in a separate directory. However, if the python sources
  should be installed alongside an extension module built with this
  module, this keyword argument can be used to override that behaviour.
  Defaults to `true`

- `subdir`: See documentation for the argument of the same name to
  [][`extension_module()`]

#### `get_install_dir()`

``` meson
string py_installation.get_install_dir(...)
```

Retrieve the directory [][`install_sources()`] will install to.

It can be useful in cases where `install_sources` cannot be used directly,
for example when using [configure_file].

This function accepts no arguments, its keyword arguments are the same
as [][`install_sources()`].

**Returns**: A string

#### `language_version()`

``` meson
string py_installation.language_version()
```

Get the major.minor python version, eg `2.7`.

The version is obtained through the `sysconfig` module.

This function expects no arguments or keyword arguments.

**Returns**: A string

#### `get_path()`

``` meson
string py_installation.get_path(path_name, fallback)
```

Get a path as defined by the `sysconfig` module.

For example:

``` meson
purelib = py_installation.get_path('purelib')
```

This function requires at least one argument, `path_name`,
which is expected to be a non-empty string.

If `fallback` is specified, it will be returned if no path
with the given name exists. Otherwise, attempting to read
a non-existing path will cause a fatal error.

**Returns**: A string

#### `has_path()`

``` meson
    bool py_installation.has_path(path_name)
```

**Returns**: true if a path named `path_name` can be retrieved with
[][`get_path()`], false otherwise.

#### `get_variable()`

``` meson
string py_installation.get_variable(variable_name, fallback)
```

Get a variable as defined by the `sysconfig` module.

For example:

``` meson
py_bindir = py_installation.get_variable('BINDIR', '')
```

This function requires at least one argument, `variable_name`,
which is expected to be a non-empty string.

If `fallback` is specified, it will be returned if no variable
with the given name exists. Otherwise, attempting to read
a non-existing variable will cause a fatal error.

**Returns**: A string

#### `has_variable()`

``` meson
    bool py_installation.has_variable(variable_name)
```

**Returns**: true if a variable named `variable_name` can be retrieved with
[][`get_variable()`], false otherwise.

## `python_dependency` object

This [dependency object] subclass will try various methods to obtain the
compiler and linker arguments, starting with pkg-config then potentially
using information obtained from python's `sysconfig` module.

It exposes the same methods as its parent class.

[find_program]: Reference-manual.md#find_program
[shared_module]: Reference-manual.md#shared_module
[external program]: Reference-manual.md#external-program-object
[dependency]: Reference-manual.md#dependency
[install_data]: Reference-manual.md#install_data
[configure_file]: Reference-manual.md#configure_file
[dependency object]: Reference-manual.md#dependency-object
[buildtarget object]: Reference-manual.md#build-target-object
