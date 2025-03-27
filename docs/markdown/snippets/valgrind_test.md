## Valgrind now fails tests if errors are found

Valgrind does not reflect an error in its exit code by default, meaning
a test may silently pass despite memory errors. Meson now exports
`VALGRIND_OPTS` such that Valgrind will exit with status 1 to indicate
an error if `VALGRIND_OPTS` is not set in the environment.
