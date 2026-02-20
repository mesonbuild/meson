## `meson dist` now accepts `-j`/`--num-processes`

`meson dist` now supports a `-j`/`--num-processes` flag to control the number of
parallel processes used during the distribution check (compilation and testing of
the generated package).  The `MESON_NUM_PROCESSES` environment variable is also
honored, consistent with other Meson commands.
