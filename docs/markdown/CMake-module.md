# CMake module

**Note**: the functionality of this module is governed by [Meson's
  rules on mixing build systems](Mixing-build-systems.md).

This module provides helper tools for generating cmake package files.
It also supports the usage of CMake based subprojects, similar to
the normal [meson subprojects](Subprojects.md).


## Usage

To use this module, just do: **`cmake = import('cmake')`**. The
following functions will then be available as methods on the object
with the name `cmake`. You can, of course, replace the name `cmake`
with anything else.

It is generally recommended to use the latest Meson version and
CMake >=3.17 for best compatibility. CMake subprojects will
usually also work with older CMake versions. However, this can
lead to unexpected issues in rare cases.

## CMake subprojects

Using CMake subprojects is similar to using the "normal" meson
subprojects. They also have to be located in the `subprojects`
directory.

Example:

```cmake
add_library(cm_lib SHARED ${SOURCES})
```

```meson
cmake = import('cmake')

# Configure the CMake project
sub_proj = cmake.subproject('libsimple_cmake')

# Fetch the dependency object
cm_lib = sub_proj.dependency('cm_lib')

executable(exe1, ['sources'], dependencies: [cm_lib])
```

The `subproject` method is almost identical to the normal meson
`subproject` function. The only difference is that a CMake project
instead of a meson project is configured.

Also, project specific CMake options can be added with the `cmake_options` key.

The returned `sub_proj` supports the same options as a "normal" subproject.
Meson automatically detects CMake build targets, which can be accessed with
the methods listed [below](#subproject-object).

It is usually enough to just use the dependency object returned by the
`dependency()` method in the build targets. This is almost identical to
using `declare_dependency()` object from a normal meson subproject.

It is also possible to use executables defined in the CMake project as code
generators with the `target()` method:

```cmake
add_executable(cm_exe ${EXE_SRC})
```

```meson
cmake = import('cmake')

# Subproject with the "code generator"
sub_pro = cmake.subproject('cmCodeGen')

# Fetch the code generator exe
sub_exe = sub_pro.target('cm_exe')

# Use the code generator
generated = custom_target(
  'cmake-generated',
  input: [],
  output: ['test.cpp'],
  command: [sub_exe, '@OUTPUT@']
)
```

It should be noted that not all projects are guaranteed to work. The
safest approach would still be to create a `meson.build` for the
subprojects in question.

### `subproject` object

This object is returned by the `subproject` function described above
and supports the following methods:

 - `dependency(target)` returns a dependency object for any CMake target.
 - `include_directories(target)` returns a meson `include_directories()`
   object for the specified target. Using this function is not necessary
   if the dependency object is used.
 - `target(target)` returns the raw build target.
 - `target_type(target)` returns the type of the target as a string
 - `target_list()` returns a list of all target *names*.
 - `get_variable(name)` fetches the specified variable from inside
   the subproject. Usually `dependency()` or `target()` should be
   preferred to extract build targets.
 - `found` returns true if the subproject is available, otherwise false
   *new in in 0.53.2*

## CMake configuration files

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
