## Tests now abort on errors by default under more sanitizers

Sanitizers like MemorySanitizer do not abort
by default on detected violations. Meson now exports `MSAN_OPTIONS` (in addition to
`ASAN_OPTIONS` and `UBSAN_OPTIONS` from a previous release) when unset in the
environment to provide sensible abort-by-default behavior.
