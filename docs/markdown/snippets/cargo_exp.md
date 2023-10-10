## Cargo subprojects is experimental

Cargo subprojects was intended to be experimental with no stability guarantees.
That notice was unfortunately missing from documentation. Meson will now start
warning about usage of experimental features and future releases might do breaking
changes.

This is aligned with our general policy regarding [mixing build systems](Mixing-build-systems.md).
