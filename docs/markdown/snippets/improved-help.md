## "meson help" now shows command line help

Command line parsing is now less surprising. "meson help" is now
equivalent to "meson --help" and "meson help <subcommand>" is
equivalent to "meson <subcommand> --help", instead of creating a build
directory called "help" in these cases.
