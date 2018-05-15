## Windows resource files dependencies

The `compile_resources()` function of the `windows` module now takes
the `depend_files:` keyword.

When using binutils's `windres`, dependencies on files `#include`'d by the
preprocessor are now automatically tracked.
