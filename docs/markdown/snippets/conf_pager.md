## Pager and colors for `meson configure` output

The output of `meson configure`, printing all options, is now more readable by
automatically using a pager (`less` by default) and colors. The pager used can
be controlled by setting `PAGER` environment variable, or `--no-pager` command
line option.
