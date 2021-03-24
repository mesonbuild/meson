## Qt Dependency uses a Factory

This separates the Pkg-config and QMake based discovery methods into two
distinct classes in the backend. This allows using
`dependency.get_variable()` and `dependency.get_pkg_config_variable()`, as
well as being a cleaner implementation.
