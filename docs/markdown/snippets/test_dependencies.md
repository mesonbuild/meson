## Test targets no longer built by default

`meson test` and the `ninja all` rule have been reworked to no longer force
unnecessary rebuilds.

`meson test` was invoking `ninja all` due to a bug if the chosen set of tests
had no build dependencies. The behavior is now the same as when tests do have
build dependencies, i.e. to only build the actual set of targets that are used
by the test. This change could cause failures when upgrading to Meson 1.7.0, if
the dependencies are not specified correctly in meson.build. Using `ninja test`
has always been guaranteed to "do the right thing" and rebuild `all` as well;
this continues to work.

`ninja all` does not rebuild all tests anymore; it should be noted that this
change means test programs are no longer guaranteed to have been built,
depending on whether those test programs were *also* defined to build by
default / marked as installable. This avoids building test-only binaries as
part of installing the project (`ninja && ninja install`), which is unnecessary
and has no use case.

Some users might have been relying on the "all" target building test
dependencies in combination with `meson test --no-rebuild` in order to skip
calling out to ninja when running tests. This might break with this change
because, when given `--no-rebuild`, Meson provides no guarantee that test
dependencies are present and up to date. The recommended workflow is to use
either `ninja test` or `ninja && meson test` but, if you wish to build test
programs and dependencies in a separate stage, you can use for example `ninja
all meson-test-prereq meson-benchmark-prereq` before `meson test --no-rebuild`.
These prereq targets have been available since meson 0.63.0.
