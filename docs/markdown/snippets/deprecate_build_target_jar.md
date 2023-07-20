## Deprecate 'jar' as a build_target type

The point of `build_target()` is that what is produced can be conditionally
changed. However, `jar()` has a significant number of non-overlapping arguments
from other build_targets, including the kinds of sources it can include. Because
of this crafting a `build_target` that can be used as a Jar and as something
else is incredibly hard to do. As such, it has been deprecated, and using
`jar()` directly is recommended.
