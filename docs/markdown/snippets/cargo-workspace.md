## Support for Cargo workspaces

When parsing `Cargo.toml` files, Meson now recognizes workspaces
and will process all the required members and any requested optional
members of the workspace.

For the time being it is recommended to regroup all Cargo dependencies inside a
single workspace invoked from the main Meson project. When invoking multiple
different Cargo subprojects from Meson, feature resolution of common
dependencies might be wrong.
