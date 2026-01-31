## Cargo C ABI libraries follows `default_library` option

When a C ABI library is produced (`crate_type` contains `staticlib`
and/or `cdylib`), Meson will follow the `default_library` option to decide
whether a shared and/or static library should be built.
