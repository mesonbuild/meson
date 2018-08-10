## Fatal warnings

A new command line option has been added: `--fatal-meson-warnings`. When enabled, any
warning message printed by Meson will be fatal and raise an exception. It is
intended to be used by developers and CIs to easily catch deprecation warnings,
or any other potential issues.
