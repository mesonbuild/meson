## Passing internal dependencies to the compiler object

Methods on the compiler object (such as `compiles`, `links`, `has_header`)
can be passed dependencies returned by `declare_dependency`, as long as they
only specify compiler/linker arguments or other dependencies that satisfy
the same requirements.
