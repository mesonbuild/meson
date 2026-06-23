## Cargo dev-dependencies and build-dependencies are now supported

The `package.dependencies()` method now accepts `dev_dependencies`
and `build_dependencies` keyword arguments. Dev-dependencies are
used by test targets, while build-dependencies are resolved with
`native: true` for use by code generators.

Workspace-level `[workspace.dev-dependencies]` and
`[workspace.build-dependencies]` tables are also properly inherited
by workspace members.
