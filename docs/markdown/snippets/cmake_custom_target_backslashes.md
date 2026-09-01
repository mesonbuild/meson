## CMake command wrappers accept arguments with backslashes

CMake subprojects can now configure `add_custom_command()`,
`add_custom_target()`, and `set_property()` calls whose arguments contain
backslashes. Meson's preload wrappers previously expanded those arguments a
second time, which could reject valid values such as regular expression
backreferences during configuration.
