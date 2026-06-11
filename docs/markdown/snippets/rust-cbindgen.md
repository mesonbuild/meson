## The Rust module includes a basic wrapper for cbindgen

This will correctly track the config.toml, and generate a rust source from the
marked C files. This handles structured_sources correctly, and also handles
depfile generation transparently.
