## Site-wide default configuration for build == host

Meson now supports a `siteconfig.ini` file. This allows OS and company wide
policy to be applied automatically. This has been added specifically to
simplify cases of operating systems using non standard paths for library
directories, as the `[paths]` section can be defined system wide. Please use
responsibly.
