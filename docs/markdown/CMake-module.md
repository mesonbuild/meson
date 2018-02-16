# CMake module

This module provides helper tools for generating cmake package files.


## Usage

To use this module, just do: **`cmake = import('cmake')`**. The
following functions will then be available as methods on the object
with the name `cmake`. You can, of course, replace the name `cmake`
with anything else.

### cmake.write_basic_package_version_file()

This function is the equivalent of the corresponding [CMake function](https://cmake.org/cmake/help/v3.11/module/CMakePackageConfigHelpers.html#generating-a-package-version-file),
it generates a `name` package version file.

* `name`: the name of the package.
* `version`: the version of the generated package file.
* `compatibility`: a string indicating the kind of compatibility, the accepted values are
`AnyNewerVersion`, `SameMajorVersion`, `SameMinorVersion` or `ExactVersion`.
It defaults to `AnyNewerVersion`. Depending on your cmake installation some kind of
compatibility may not be available.
* `install_dir`: optional installation directory, it defaults to `$(libdir)/cmake/$(name)`


Example:

```meson
cmake = import('cmake')

cmake.write_basic_package_version_file(name: 'myProject', version: '1.0.0')
```

### cmake.configure_package_config_file()

This function is the equivalent of the corresponding [CMake function](https://cmake.org/cmake/help/v3.11/module/CMakePackageConfigHelpers.html#generating-a-package-configuration-file),
it generates a `name` package configuration file from the `input` template file. Just like the cmake function
in this file the `@PACKAGE_INIT@` statement will be replaced by the appropriate piece of cmake code.
The equivalent `PATH_VARS` argument is given through the `configuration` parameter.

* `name`: the name of the package.
* `input`: the template file where that will be treated for variable substitutions contained in `configuration`.
* `install_dir`: optional installation directory, it defaults to `$(libdir)/cmake/$(name)`.
* `configuration`: a `configuration_data` object that will be used for variable substitution in the template file.


Example:

meson.build:

```meson
cmake = import('cmake')

conf = configuration_data()
conf.set_quoted('VAR', 'variable value')

cmake.configure_package_config_file(
    name: 'myProject',
    input: 'myProject.cmake.in',
    configuration: conf
)
```

myProject.cmake.in:

```text
@PACKAGE_INIT@

set(MYVAR VAR)
```
