## The Meson test program supports a new "--interactive" argument

`meson test --interactive` invokes tests with stdout, stdin and stderr
connected directly to the calling terminal. This can be useful when running
integration tests that run in containers or virtual machines which can spawn a
debug shell if a test fails.
