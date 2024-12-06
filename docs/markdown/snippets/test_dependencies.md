## Test targets no longer built by default

The `ninja test` / `meson test` rules have been reworked to no longer force
tests to be built unnecessarily. The correct, guaranteed workflow for this has
been to either run `ninja test` or `meson test`, both of which rebuild
dependencies on demand. *Also* building test-only binaries as part of
installing the project (`ninja && ninja install`) was unnecessary and has no
use case.

Some users might have been relying on the "all" target building test
dependencies in combination with `meson test --no-rebuild` in order to skip
calling out to ninja when running tests. The `--no-rebuild` option has always
been intended for expert usage -- you must provide your own guarantees that it
will work -- and it should be noted that this change means test programs are no
longer guaranteed to have been built, depending on whether those test programs
were *also* defined to build by default / marked as installable. The desired
behavior of building test programs in a separate stage can be restored by
building `ninja all meson-test-prereq` (or `meson-benchmark-prereq` for running
benchmarks), as these prereq targets have been available since meson 0.63.0.
