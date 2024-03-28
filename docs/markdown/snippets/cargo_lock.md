## Added support `Cargo.lock` file

When a (sub)project has a `Cargo.lock` file at its root, it is loaded to provide
an automatic fallback for dependencies it defines, fetching code from
https://crates.io or git. This is identical as providing `subprojects/*.wrap`,
see [cargo wraps](Wrap-dependency-system-manual.md#cargo-wraps) dependency naming convention.
