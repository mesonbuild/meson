## Support for clippy-driver as a rustc wrapper

Clippy is a popular linting tool for Rust, and is invoked in place of rustc as a
wrapper. Unfortunately it doesn't proxy rustc's output, so we need to have a
small wrapper around it so that Meson can correctly detect the underlying rustc,
but still display clippy
