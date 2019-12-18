## Improved CMake subprojects support

With this release even more CMake projects are supported via
[CMake subprojects](CMake-module.md#cmake-subprojects) due to these internal
improvements:

- Use the CMake file API for CMake >=3.14
- Handle the explicit dependencies via `add_dependency`
- Basic support for `add_custom_target`
- Improved `add_custom_command` support
- Object library support on Windows
