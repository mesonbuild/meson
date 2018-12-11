---
short-description: Meson's API to integrate Meson support into an IDE
...

# IDE integration

Meson has exporters for Visual Studio and XCode, but writing a custom backend for every IDE out there is not a scalable approach. To solve this problem, Meson provides an API that makes it easy for any IDE or build tools to integrate Meson builds and provide an experience comparable to a solution native to the IDE.

All the resources required for such a IDE integration can be found in the `meson-info` directory in the build directory.

The first thing to do when setting up a Meson project in an IDE is to select the source and build directories. For this example we assume that the source resides in an Eclipse-like directory called `workspace/project` and the build tree is nested inside it as `workspace/project/build`. First, we initialize Meson by running the following command in the source directory.

    meson builddir

With this command meson will configure the project and also generate introspection information that is stored in `intro-*.json` files in the `meson-info` directory. All files will be automatically updated when meson is (re)configured, or the build options change. Thus, an IDE can watch for changes in this directory to know when something changed.

The `meson-info` directory should contain the following files:

 File                            | Description
 ------------------------------- | ---------------------------------------------------------------------
 `intro-benchmarks.json`         | Lists all benchmarks
 `intro-buildoptions.json`       | Contains a full list of meson configuration options for the project
 `intro-buildsystem_files.json`  | Full list of all meson build files
 `intro-dependencies.json`       | Lists all dependencies used in the project
 `intro-installed.json`          | Contains mapping of files to their installed location
 `intro-projectinfo.json`        | Stores basic information about the project (name, version, etc.)
 `intro-targets.json`            | Full list of all build targets
 `intro-tests.json`              | Lists all tests with instructions how to run them

The content of the JSON files is further specified in the remainder of this document.

## The `targets` section

The most important file for an IDE is probably `intro-targets.json`. Here each target with its sources and compiler parameters is specified. The JSON format for one target is defined as follows:

```json
{
    "name": "Name of the target",
    "id": "The internal ID meson uses",
    "type": "<TYPE>",
    "filename": ["list", "of", "generate", "files"],
    "build_by_default": true / false,
    "sources": [],
    "installed": true / false,
}
```

If the key `installed` is set to `true`, the key `install_filename` will also be present. It stores the installation location for each file in `filename`. If one file in `filename` is not installed, its corresponding install location is set to `null`.

A target usually generates only one file. However, it is possible for custom targets to have multiple outputs.

### Target sources

The `intro-sources.json` file stores a list of all source objects of the target. With this information, an IDE can provide code completion for all source files.

```json
{
    "language": "language ID",
    "compiler": ["The", "compiler", "command"],
    "parameters": ["list", "of", "compiler", "parameters"],
    "sources": ["list", "of", "all", "source", "files", "for", "this", "language"],
    "generated_sources": ["list", "of", "all", "soruce", "files", "that", "where", "generated", "somewhere", "else"]
}
```

### Possible values for `type`

The following table shows all valid types for a target.

 value of `type`  | Description
 ---------------- | -------------------------------------------------------------------------------------------------
 `executable`     | This target will generate an executable file
 `static library` | Target for a static library
 `shared library` | Target for a shared library
 `shared module`  | A shared library that is meant to be used with dlopen rather than linking into something else
 `custom`         | A custom target
 `unknown target` | The current target format is unknown. This is probably a bug

## Build Options

The list of all build options (build type, warning level, etc.) is stored in the `intro-buildoptions.json` file. Here is the JSON format for each option.

```json
{
    "name": "name of the option",
    "description": "the description",
    "type": "type ID",
    "value": "value depends on type",
    "section": "section ID"
}
```

The supported types are:

 - string
 - boolean
 - combo
 - integer
 - array

For the type `combo` the key `choices` is also present. Here all valid values for the option are stored.

The possible values for `section` are:

 - core
 - backend
 - base
 - compiler
 - directory
 - user
 - test

To set the options, use the `meson configure` command.

Since Meson 0.50.0 it is also possible to get the default buildoptions
without a build directory by providing the root `meson.build` instead of a
build directory to `meson introspect --buildoptions`.

Running `--buildoptions` without a build directory produces the same output as running
it with a freshly configured build directory.

However, this behavior is not guaranteed if subprojects are present. Due to internal
limitations all subprojects are processed even if they are never used in a real meson run.
Because of this options for the subprojects can differ.

## Tests

Compilation and unit tests are done as usual by running the `ninja` and `ninja test` commands. A JSON formatted result log can be found in `workspace/project/builddir/meson-logs/testlog.json`.

When these tests fail, the user probably wants to run the failing test in a debugger. To make this as integrated as possible, extract the tests from the `tests` and `benchmarks` entries.
This provides you with all the information needed to run the test: what command to execute, command line arguments and environment variable settings.

```json
{
    "name": "name of the test",
    "workdir": "the working directory (can be null)",
    "timeout": "the test timeout",
    "suite": ["list", "of", "test", "suites"],
    "is_parallel": true / false,
    "cmd": ["command", "to", "run"],
    "env": {
        "VARIABLE1": "value 1",
        "VARIABLE2": "value 2"
    }
}
```

# Programmatic interface

Meson also provides the `meson introspect` for project introspection via the command line. Use `meson introspect -h` to see all available options.

This API can also work without a build directory for the `--projectinfo` command.

# Existing integrations

- [Gnome Builder](https://wiki.gnome.org/Apps/Builder)
- [Eclipse CDT](https://www.eclipse.org/cdt/) (experimental)
- [Meson Cmake Wrapper](https://github.com/prozum/meson-cmake-wrapper) (for cmake IDEs)