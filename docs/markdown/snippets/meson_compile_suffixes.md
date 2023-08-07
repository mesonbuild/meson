## Meson compile command now accepts suffixes for TARGET

The syntax for specifying a target for meson compile is now
`[PATH_TO_TARGET/]TARGET_NAME.TARGET_SUFFIX[:TARGET_TYPE]` where
`TARGET_SUFFIX` is the suffix argument given in the build target
within meson.build. It is optional and `TARGET_NAME` remains
sufficient if it uniquely resolves to one single target.
