## Parallelized `meson subprojects` commands

All `meson subprojects` commands are now run on each subproject in parallel by
default. The number of processes can be controlled with `--num-processes`
argument.

This speeds up considerably IO-bound operations such as downloads and git fetch.
