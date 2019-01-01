---
short-description: Meson's API to integrate Meson support into an IDE
...

# IDE integration

Meson has exporters for Visual Studio and XCode, but writing a custom backend for every IDE out there is not a scalable approach. To solve this problem, Meson provides an API that makes it easy for any IDE or build tool to integrate Meson builds and provide an experience comparable to a solution native to the IDE.

The basic tool for this is `meson introspect`.

The first thing to do when setting up a Meson project in an IDE is to select the source and build directories. For this example we assume that the source resides in an Eclipse-like directory called `workspace/project` and the build tree is nested inside it as `workspace/project/build`. First we initialise Meson by running the following command in the source directory.

    meson builddir

For the remainder of the document we assume that all commands are executed inside the build directory unless otherwise specified.

The first thing you probably want is to get a list of top level targets. For that we use the introspection tool. It comes with extensive command line help so we recommend using that in case problems appear.

    meson introspect --targets

The JSON formats will not be specified in this document. The easiest way of learning them is to look at sample output from the tool.

Once you have a list of targets, you probably need the list of source files that comprise the target. To get this list for a target, say `exampletarget`, issue the following command.

    meson introspect --target-files exampletarget

In order to make code completion work, you need the compiler flags for each compilation step. Meson does not provide this itself, but the Ninja tool Meson uses to build does provide it. To find out the compile steps necessary to build target foo, issue the following command.

    ninja -t commands foo

Note that if the target has dependencies (such as generated sources), then the commands for those show up in this list as well, so you need to do some filtering. Alternatively you can grab every command invocation in the [Clang tools db](https://clang.llvm.org/docs/JSONCompilationDatabase.html) format that is written to a file called `compile_commands.json` in the build directory.

## Build Options

The next thing to display is the list of options that can be set. These include build type and so on. Here's how to extract them.

    meson introspect --buildoptions

This command returns a list of all supported buildoptions with the format:

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

When these tests fail, the user probably wants to run the failing test in a debugger. To make this as integrated as possible, extract the test test setups with this command.

    meson introspect --tests

This provides you with all the information needed to run the test: what command to execute, command line arguments and environment variable settings.

# Existing integrations

- [Gnome Builder](https://wiki.gnome.org/Apps/Builder)
- [Eclipse CDT](https://www.eclipse.org/cdt/) (experimental)
- [Meson Cmake Wrapper](https://github.com/prozum/meson-cmake-wrapper) (for cmake IDEs)