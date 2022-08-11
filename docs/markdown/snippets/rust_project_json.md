## Generates rust-project.json when there are Rust targets

This is a format similar to compile_commands.json, but specifically used by the
official rust LSP, rust-analyzer. It is generated automatically if there are
Rust targets, and is placed in the build directory.
