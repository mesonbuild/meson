## Change to handling of linker arguments for Rust

Since the Rust compiler integrates the compiler and linker phase, previous
Meson versions did not obey `link_args`, `add_project_link_arguments`
or `add_global_link_arguments`.

Starting in this version, `add_project_link_arguments()`,
`add_global_link_arguments()`, and the `link_args` keyword argument are
supported for Rust.  They wrap the arguments with `-Clink-arg=` when
invoking rustc, and are only included when creating binary or shared
library crates.

Likewise, methods such as `has_link_argument()` now wrap the arguments
being tested with `-Clink-arg=`.
