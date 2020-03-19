## Dynamic Linker environment variables actually match docs

The docs have always claimed that the Dynamic Linker environment variable
should be `${COMPILER_VAR}_LD`, but that's only the case for about half of
the variables. The other half are different. In 0.54.0 the variables match.
The old variables are still supported, but are deprecated and raise a
deprecation warning.
