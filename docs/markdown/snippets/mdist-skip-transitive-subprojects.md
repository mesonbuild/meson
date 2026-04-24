## `meson dist --include-subprojects` no longer fails on transitive subprojects

`meson dist --include-subprojects` previously failed with a
`FileNotFoundError` when a subproject itself had a subproject (i.e. a
transitive subproject) that was not present as a directory in the
top-level `subprojects/` folder. Such transitive subprojects are
already included as part of their parent subproject's source tree, so
they are now silently skipped rather than causing an error.
