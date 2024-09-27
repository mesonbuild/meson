## Default to printing deprecations when no minimum version is specified.

For a long time, the [[project]] function has supported specifying the minimum
`meson_version:` needed by a project. When this is used, deprecated features
from before that version produce warnings, as do features which aren't
available in all supported versions.

When no minimum version was specified, meson didn't warn you even about
deprecated functionality that might go away in an upcoming semver major release
of meson.

Now, meson will treat an unspecified minimum version following semver:

- For new features introduced in the current meson semver major cycle
  (currently: all features added since 1.0) a warning is printed. Features that
  have been available since the initial 1.0 release are assumed to be widely
  available.

- For features that have been deprecated by any version of meson, a warning is
  printed. Since no minimum version was specified, it is assumed that the
  project wishes to follow the latest and greatest functionality.

These warnings will overlap for functionality that was both deprecated and
replaced with an alternative in the current release cycle. The combination
means that projects without a minimum version specified are assumed to want
broad compatibility with the current release cycle (1.x).

Projects that specify a minimum `meson_version:` will continue to only receive
actionable warnings based on their current minimum version.
