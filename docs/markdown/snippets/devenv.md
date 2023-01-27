## Dump devenv into file and select format

`meson devenv --dump [<filename>]` command now takes an optional filename argument
to write the environment into a file instead of printing to stdout.

A new `--dump-format` argument has been added to select which shell format
should be used. There are currently 3 formats supported:
- `sh`: Lines are in the format `VAR=/prepend:$VAR:/append`.
- `export`: Same as `sh` but with extra `export VAR` lines.
- `vscode`: Same as `sh` but without `$VAR` substitution because they do not
  seems to be properly supported by vscode.
