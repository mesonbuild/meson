## Deprecate `build_always`

Setting `build_always` to `true` for a custom target not only marks the target
to be always considered out of date, but also adds it to the set of default
targets. This option is therefore deprecated and the new option
`build_always_stale` is introduced.

`build_always_stale` *only* marks the target to be always considered out of
date, but does not add it to the set of default targets. The old behaviour can
be achieved by combining `build_always_stale` with `build_by_default`.

The documentation has been updated accordingly.
