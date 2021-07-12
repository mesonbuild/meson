## `compiler.check_header` includes build dir in search path

Checking for headers that are configured via `configure_file` is now more intuitive. Previously the build dir had to be included manually with the `include_directories` option. Now the configured headers will be found by default.