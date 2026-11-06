## Custom target commands use relative paths with the Visual Studio backend

With the Visual Studio backends, custom target commands are run from the
directory of their project file. Paths passed to the command (inputs,
outputs, `@SOURCE_ROOT@`, `@BUILD_ROOT@`, `@CURRENT_SOURCE_DIR@`,
`@PRIVATE_DIR@`, files and other custom targets) were previously absolute.
They are now relative to that directory, as they already were relative to the
build directory with the Ninja backend. Targets created by modules that need
absolute paths, such as `gnome.mkenums()`, still get them.
