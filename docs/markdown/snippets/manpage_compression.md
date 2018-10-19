## Manpages are no longer compressed implicitly

Earlier, the `install_man` command has automatically compressed installed
manpages into `.gz` format. This collided with manpage compression hooks
already used by various distributions. Now, manpages are installed uncompressed
and distributors are expected to handle compressing them according to their own
compression preferences.
