## `dependency(version:)` now applies to all dependency types

Previously, version constraints were only enforced for dependencies found using
the pkg-config dependency provider.  These constraints now apply to dependencies
found using any dependency provider.

Some combinations of dependency, host and method do not currently support
discovery of the version.  In these cases, the dependency will not be found if a
version constraint is applied, otherwise the `version()` method for the
dependency object will return `'unknown'`.

(If discovering the version in one of these combinations is important to you,
and a method exists to determine the version in that case, please file an issue
with as much information as possible.)
