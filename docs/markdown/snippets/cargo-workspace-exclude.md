## Support for `workspace.exclude` in Cargo manifests

Directories that are listed in the `workspace.exclude` field of `Cargo.toml`
are not treated as workspace members anymore.  Such packages can still be
used through a `path` dependency, as long as they are placed directly in the
`subprojects` directory.  This allows using nested workspaces if needed.
