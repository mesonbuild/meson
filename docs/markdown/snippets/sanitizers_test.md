## Tests now abort on errors by default under sanitizers

Sanitizers like AddressSanitizer and UndefinedBehaviorSanitizer do not abort
by default on detected violations. Meson now exports `ASAN_OPTIONS` and `UBSAN_OPTIONS`
when unset in the environment to provide sensible abort-by-default behavior.
