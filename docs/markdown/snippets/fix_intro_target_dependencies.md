## Target introspection reports all direct target dependencies

The `depends` entry in `intro-targets.json` now reports direct target
dependencies from target inputs, generated sources, extracted objects,
internal linking, and explicit `depends` arguments. Previously it only
reported the `dependencies` attribute used by alias and run targets, so most
build target and custom target dependencies were omitted.
