## Passing `-C default-linker-libraries` to rustc

When calling rustc, Meson now passes the `-C default-linker-libraries` option.
While rustc passes the necessary libraries for Rust programs, they are rarely
enough for mixed Rust/C programs.
