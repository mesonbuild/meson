## Compiler options can be set per subproject

All compiler options can now be set per subproject. See
[here](Build-options.md#specifying-options-per-subproject) for details on how
the default value is inherited from main project.

This is useful for example when the main project requires C++11 but a subproject
requires C++14. The `cpp_std` value from subproject's `default_options` is now
respected.
