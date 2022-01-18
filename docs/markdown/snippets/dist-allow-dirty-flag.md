## Added optional '--allow-dirty' flag for the 'dist' command

An optional `--allow-dirty` flag has been added to the `dist` command.

Previously, if uncommitted changes were present, Meson would warn about
this but continue with the dist process. It now errors out instead. The
error can be suppressed by using the `--allow-dirty` option.
