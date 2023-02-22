## Rust now supports the b_ndebug option

Which controls the `debug_assertions` cfg, which in turn controls
`debug_assert!()` macro. This macro is roughly equivalent to C's `assert()`, as
it can be toggled with command line options, unlike Rust's `assert!()`, which
cannot be turned off, and is not designed to be.
